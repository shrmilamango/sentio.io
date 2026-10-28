"""
Sentio model service.

Loads a trained checkpoint from ML/models/<tag>/ and serves predictions on
port 8001. The main API (api/) calls this when USE_FAKE_MODEL=False.

Run:  python serve.py                 (uses models/hingroberta, the best model)
      python serve.py --tag xlmr      (any other trained model)

POST /predict  {"text": "..."}  -> same response shape as api/app/fake_model.py
GET  /health                     -> model name + its test scores
"""
import argparse
import hmac
import json
import os
import re
import threading
import time
from pathlib import Path

import torch
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from torch import nn
from transformers import AutoConfig, AutoModel, AutoTokenizer

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="hingroberta")
ap.add_argument("--port", type=int, default=8001)
args, _ = ap.parse_known_args()

MODEL_DIR = HERE / "models" / args.tag
CFG = json.loads((MODEL_DIR / "sentio_config.json").read_text(encoding="utf-8"))
HEADS, CLASSES = CFG["heads"], CFG["classes"]
RESULTS_FILE = HERE / "results" / f"{args.tag}.json"
RESULTS = json.loads(RESULTS_FILE.read_text(encoding="utf-8")) if RESULTS_FILE.exists() else {}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class MultiHead(nn.Module):
    """Must match the class in train.py (same attribute names)."""
    def __init__(self):
        super().__init__()
        self.encoder = AutoModel.from_config(AutoConfig.from_pretrained(CFG["base_model"]))
        hidden = self.encoder.config.hidden_size
        self.drop = nn.Dropout(0.1)
        self.heads = nn.ModuleDict({h: nn.Linear(hidden, len(CLASSES[h])) for h in HEADS})

    def forward(self, ids=None, mask=None, embeds=None):
        out = self.encoder(input_ids=ids, inputs_embeds=embeds, attention_mask=mask).last_hidden_state[:, 0]
        return {h: head(self.drop(out)) for h, head in self.heads.items()}


tok = AutoTokenizer.from_pretrained(MODEL_DIR)
model = MultiHead()
model.load_state_dict(torch.load(MODEL_DIR / "model.pt", map_location="cpu", weights_only=True))
model.to(device).eval()
# Gradients are needed only for the input embeddings (word importance), not the
# weights; without this every request would also fill a weight-sized gradient buffer.
model.requires_grad_(False)
_lock = threading.Lock()   # one prediction at a time on the GPU

# Shared secret: when set, the API must send it in X-Sentio-Token (use this when
# the service is public through ngrok). Empty = open, fine on localhost.
TOKEN = os.environ.get("ML_SERVICE_TOKEN", "")


def check_token(x_sentio_token: str = Header("", include_in_schema=False)):
    if TOKEN and not hmac.compare_digest(x_sentio_token, TOKEN):
        raise HTTPException(status_code=401, detail="Bad or missing X-Sentio-Token")

# ---- language tagging (lexicon, same word list used to build the dataset) ----
_hw = HERE.parent / "Dataset" / "hindi_words.txt"
HINDI = set(w.strip().lower() for w in _hw.read_text(encoding="utf-8").splitlines() if w.strip()) if _hw.exists() else set()
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]")
WORD = re.compile(r"[\w']+|" + EMOJI.pattern)

def lang_of(w: str) -> str:
    if EMOJI.fullmatch(w):
        return "emoji"
    if re.search(r"[ऀ-ॿ]", w):
        return "hi_deva"
    if w.lower() in HINDI:
        return "hi_roman"
    return "en" if re.fullmatch(r"[A-Za-z']+", w) else "other"

# keyword hints used ONLY to locate a span for an aspect the model predicted
SPAN_HINTS = {
    "delivery_time": ["late", "der", "time", "jaldi", "fast", "slow", "minute", "ghante", "delivery"],
    "food_quality": ["khana", "food", "taste", "tasty", "swad", "thanda", "garam", "fresh", "quality"],
    "packaging": ["packing", "packaging", "pack", "container", "leak", "dabba"],
    "delivery_partner": ["delivery boy", "rider", "partner", "bhaiya", "delivery wala"],
    "app_experience": ["app", "crash", "login", "payment", "update", "otp"],
    "price_offers": ["price", "mehnga", "mahanga", "costly", "coupon", "offer", "discount", "charge", "rate", "sasta"],
    "refund_support": ["refund", "support", "customer care", "complaint", "return", "replace", "paisa wapas"],
}

def find_span(text: str, aspect: str):
    low = text.lower()
    for kw in SPAN_HINTS.get(aspect, []):
        i = low.find(kw)
        if i >= 0:
            return [i, i + len(kw)]
    return None


app = FastAPI(title="Sentio model service", docs_url=None, redoc_url=None, openapi_url=None)


class Req(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


@app.get("/health", dependencies=[Depends(check_token)])
def health():
    t = RESULTS.get("test", {})
    return {"status": "ok", "tag": args.tag, "base_model": CFG["base_model"], "device": str(device),
            "train_size": CFG.get("train_size"),
            "test_overall_macro_f1": t.get("overall_macro_f1"),
            "test_aspect_detection_f1": t.get("aspect_detection_f1_avg"),
            "test_aspect_sentiment_f1": t.get("aspect_sentiment_macro_f1_avg")}


@app.post("/predict", dependencies=[Depends(check_token)])
def predict(req: Req):
    with _lock:
        return _predict(req)


def _predict(req: Req):
    t0 = time.perf_counter()
    text = req.text
    # Tokenise the raw text exactly as in training, then map sub-word tokens
    # back to words using character offsets (works for BERT and RoBERTa models).
    spans = [(m.group(), m.start(), m.end()) for m in WORD.finditer(text)] or [(text, 0, len(text))]
    words = [w for w, _, _ in spans]
    enc = tok(text, truncation=True, max_length=CFG["max_len"], return_tensors="pt",
              return_offsets_mapping=True)
    offsets = enc.pop("offset_mapping")[0].tolist()
    ids, mask = enc["input_ids"].to(device), enc["attention_mask"].to(device)

    # forward with gradients on the input embeddings (for word attributions)
    embeds = model.encoder.get_input_embeddings()(ids).detach().requires_grad_(True)
    out = model(embeds=embeds, mask=mask)
    probs = {h: torch.softmax(out[h][0].float(), -1) for h in HEADS}

    oc = CLASSES["overall_sentiment"]
    direction = out["overall_sentiment"][0, oc.index("positive")] - out["overall_sentiment"][0, oc.index("negative")]
    direction.backward()
    sub_scores = (embeds.grad[0] * embeds[0]).sum(-1).detach().cpu().tolist()

    word_scores = [0.0] * len(words)
    for pos, (a, b) in enumerate(offsets):
        if b <= a:                      # special tokens have empty offsets
            continue
        for wi, (_, ws, we) in enumerate(spans):
            if a < we and b > ws:       # token overlaps this word
                word_scores[wi] += sub_scores[pos]
                break
    peak = max((abs(s) for s in word_scores), default=0) or 1.0
    tokens = [{"text": w, "lang": lang_of(w), "weight": round(s / peak, 3)} for w, s in zip(words, word_scores)]

    p = probs["overall_sentiment"]
    k = int(p.argmax())
    aspects = []
    for a in HEADS[1:]:
        pa = probs[a]
        j = int(pa.argmax())
        label = CLASSES[a][j]
        if label != "none":
            aspects.append({"aspect": a, "polarity": label, "confidence": round(float(pa[j]), 3),
                            "span": find_span(text, a)})

    counts = {}
    for tkn in tokens:
        counts[tkn["lang"]] = counts.get(tkn["lang"], 0) + 1
    dist = {kk: round(v / len(tokens), 2) for kk, v in counts.items()}

    return {
        "normalized_text": re.sub(r"(.)\1{2,}", r"\1", text.lower()).strip(),
        "polarity": oc[k],
        "confidence": round(float(p[k]), 3),
        "sarcasm": False,
        "language_distribution": dist,
        "tokens": tokens,
        "aspects": aspects,
        "model_version": args.tag,
        "latency_ms": max(1, int((time.perf_counter() - t0) * 1000)),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port)
