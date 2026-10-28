"""
Fine-tune a multilingual transformer for aspect-based sentiment analysis
of code-mixed Hinglish food delivery reviews.

One shared encoder, eight classification heads:
    overall sentiment           negative / neutral / positive
    7 aspects (one head each)   none / negative / positive

Loss = sum of cross-entropy over the 8 heads, with class weights so rare
labels (positive) still count.

Best epoch chosen on VAL. TEST is scored once, with the best checkpoint.

Run:   python train.py                               (MuRIL, default)
       python train.py --model bert-base-multilingual-cased --tag mbert
       python train.py --model xlm-roberta-base --tag xlmr
       python train.py --model l3cube-pune/hing-roberta --tag hingroberta
Log:   ML/logs/train_<tag>.log
Output ML/models/<tag>/   ML/results/<tag>.json   ML/results/<tag>_test_predictions.csv
"""
import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

from labels import ASPECTS, ASPECT_CLASSES, OVERALL, aspect_label
from metrics import score

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--model", default="google/muril-base-cased")
ap.add_argument("--tag", default="muril_v1")
ap.add_argument("--splits", default="splits_v1")
ap.add_argument("--epochs", type=int, default=6)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--lr", type=float, default=3e-5)
ap.add_argument("--max_len", type=int, default=96)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--no_amp", action="store_true",
                help="train in full float32 (slower, but some models e.g. MuRIL fail to learn in float16)")
args = ap.parse_args()

LOG = HERE / "logs" / f"train_{args.tag}.log"
LOG.parent.mkdir(exist_ok=True)
LOG.write_text("", encoding="utf-8")


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
log(f"model={args.model}  device={device}"
    + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else ""))

# ---------------- data ----------------
def load(name):
    df = pd.read_csv(HERE / args.splits / f"{name}.csv", dtype=str, keep_default_na=False)
    for a in ASPECTS:
        df[a] = df[a].map(aspect_label)
    return df

train_df, val_df, test_df = load("train"), load("val"), load("test")
log(f"train {len(train_df)}  val {len(val_df)}  test {len(test_df)}")

HEADS = ["overall_sentiment"] + ASPECTS
CLASSES = {"overall_sentiment": OVERALL, **{a: ASPECT_CLASSES for a in ASPECTS}}

tok = AutoTokenizer.from_pretrained(args.model)


class Reviews(Dataset):
    def __init__(self, df):
        self.enc = tok(df.review_text.tolist(), truncation=True, max_length=args.max_len,
                       padding="max_length", return_tensors="pt")
        self.y = torch.tensor(np.stack([df[h].map({c: i for i, c in enumerate(CLASSES[h])}).values
                                        for h in HEADS], axis=1), dtype=torch.long)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, i):
        return self.enc["input_ids"][i], self.enc["attention_mask"][i], self.y[i]


train_dl = DataLoader(Reviews(train_df), batch_size=args.batch, shuffle=True)
val_dl = DataLoader(Reviews(val_df), batch_size=64)
test_dl = DataLoader(Reviews(test_df), batch_size=64)


def class_weights(h):
    counts = train_df[h].value_counts().reindex(CLASSES[h], fill_value=0).values.astype(float)
    w = 1.0 / np.sqrt(np.maximum(counts, 1))     # sqrt-inverse frequency
    w = w / w.mean()
    return torch.tensor(np.minimum(w, 10.0), dtype=torch.float, device=device)


# ---------------- model ----------------
class MultiHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(args.model)
        hidden = self.encoder.config.hidden_size
        self.drop = nn.Dropout(0.1)
        self.heads = nn.ModuleDict({h: nn.Linear(hidden, len(CLASSES[h])) for h in HEADS})

    def forward(self, ids, mask):
        out = self.encoder(input_ids=ids, attention_mask=mask).last_hidden_state[:, 0]
        out = self.drop(out)
        return {h: head(out) for h, head in self.heads.items()}


model = MultiHead().to(device)
losses = {h: nn.CrossEntropyLoss(weight=class_weights(h)) for h in HEADS}
opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
steps = len(train_dl) * args.epochs
sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
use_amp = device.type == "cuda" and not args.no_amp
log(f"mixed precision (float16): {use_amp}   lr={args.lr}  epochs={args.epochs}")
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)


@torch.no_grad()
def predict(dl, df):
    model.eval()
    preds = {h: [] for h in HEADS}
    for ids, mask, _ in dl:
        with torch.autocast(device.type, enabled=use_amp):
            logits = model(ids.to(device), mask.to(device))
        for h in HEADS:
            preds[h] += [CLASSES[h][i] for i in logits[h].argmax(-1).cpu().tolist()]
    return pd.DataFrame(preds, index=df.index)


# ---------------- train ----------------
OUT_DIR = HERE / "models" / args.tag
OUT_DIR.mkdir(parents=True, exist_ok=True)
best, history = -1.0, []
for epoch in range(1, args.epochs + 1):
    model.train()
    t0, total = time.time(), 0.0
    for step, (ids, mask, y) in enumerate(train_dl, 1):
        ids, mask, y = ids.to(device), mask.to(device), y.to(device)
        with torch.autocast(device.type, enabled=use_amp):
            logits = model(ids, mask)
            loss = sum(losses[h](logits[h].float(), y[:, i]) for i, h in enumerate(HEADS))
        opt.zero_grad()
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(opt); scaler.update(); sched.step()
        total += loss.item()
        if step % 20 == 0 or step == len(train_dl):
            log(f"epoch {epoch}/{args.epochs}  step {step}/{len(train_dl)}  loss {total/step:.3f}")

    v = score(val_df, predict(val_dl, val_df))
    history.append({"epoch": epoch, "train_loss": round(total / len(train_dl), 4),
                    **{k: v[k] for k in ("overall_macro_f1", "aspect_detection_f1_avg",
                                         "aspect_sentiment_macro_f1_avg", "selection_score")}})
    log(f"epoch {epoch} done in {time.time()-t0:.0f}s | VAL overall F1 {v['overall_macro_f1']:.3f} "
        f"| aspect detect {v['aspect_detection_f1_avg']:.3f} | aspect sent {v['aspect_sentiment_macro_f1_avg']:.3f} "
        f"| score {v['selection_score']:.3f}")
    if v["selection_score"] > best:
        best = v["selection_score"]
        torch.save(model.state_dict(), OUT_DIR / "model.pt")
        log(f"  new best, saved")

# ---------------- test (once, best checkpoint) ----------------
model.load_state_dict(torch.load(OUT_DIR / "model.pt", map_location=device, weights_only=True))
tok.save_pretrained(OUT_DIR)
(OUT_DIR / "sentio_config.json").write_text(json.dumps({
    "base_model": args.model, "max_len": args.max_len, "heads": HEADS,
    "classes": CLASSES, "train_size": len(train_df), "splits": args.splits}, indent=2), encoding="utf-8")

test_pred = predict(test_dl, test_df)
t = score(test_df, test_pred)
result = {"model": args.model, "tag": args.tag, "args": vars(args), "best_val_score": best,
          "history": history, "test": t}
(HERE / "results").mkdir(exist_ok=True)
(HERE / "results" / f"{args.tag}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

side = test_df[["id", "review_text"] + HEADS].copy()
for h in HEADS:
    side[f"pred_{h}"] = test_pred[h]
side["any_error"] = (side[HEADS].values != side[[f"pred_{h}" for h in HEADS]].values).any(axis=1)
side.to_csv(HERE / "results" / f"{args.tag}_test_predictions.csv", index=False, encoding="utf-8")

log(f"TEST overall macro-F1 {t['overall_macro_f1']:.3f}  acc {t['overall_accuracy']:.3f}  "
    f"per class {t['overall_f1_per_class']}")
log(f"TEST aspect detection F1 {t['aspect_detection_f1_avg']:.3f}  aspect sentiment F1 {t['aspect_sentiment_macro_f1_avg']:.3f}")
for a, r in t["aspects"].items():
    log(f"   {a:<17} detect {r['detection_f1']:.3f}  sentiment {r['sentiment_macro_f1']:.3f}")
log("TRAINING DONE")
