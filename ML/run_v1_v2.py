"""
Train HingRoBERTa on dataset v1 and v2 on this laptop's GPU, same settings,
same frozen test split, then rebuild the comparison table.

Run:  python run_v1_v2.py      (VS Code: "ML 3 - Train HingRoBERTa v1 + v2")
Logs: ML/logs/train_hingroberta_local_v1.log, ..._v2.log, logs/run_v1_v2.log
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "logs" / "run_v1_v2.log"
LOG.write_text("", encoding="utf-8")


def log(msg):
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


for tag, splits in [("hingroberta_local_v1", "splits_v1"), ("hingroberta_local_v2", "splits_v2")]:
    log(f"=== training {tag} on {splits} ===")
    rc = subprocess.run([sys.executable, "train.py", "--model", "l3cube-pune/hing-roberta",
                         "--tag", tag, "--splits", splits], cwd=HERE).returncode
    log(f"{tag} exit code {rc}")
    if rc != 0:
        log("RUN FAILED"); sys.exit(rc)

subprocess.run([sys.executable, "compare_results.py"], cwd=HERE)
log("ALL DONE")
