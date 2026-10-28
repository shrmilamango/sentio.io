"""
Creates ML/venv and installs everything needed for scraping and training.

Detects an NVIDIA GPU: if present, installs the CUDA build of PyTorch
(much faster training); otherwise the CPU build.

Run once with your normal Python 3.12 (VS Code: "ML 1 - Setup environment").
Log: ML/logs/setup.log
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / "venv"
PY = VENV / "Scripts" / "python.exe"
LOG = HERE / "logs" / "setup.log"
LOG.parent.mkdir(exist_ok=True)
LOG.write_text("", encoding="utf-8")


def log(msg: str) -> None:
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def run(cmd: list[str]) -> None:
    log("$ " + " ".join(str(c) for c in cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        log("  " + line.rstrip())
    if proc.wait() != 0:
        log(f"SETUP FAILED (exit {proc.returncode})")
        sys.exit(1)


log(f"Python: {sys.version}")

gpu = False
smi = shutil.which("nvidia-smi")
if smi:
    out = subprocess.run([smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                         capture_output=True, text=True)
    if out.returncode == 0 and out.stdout.strip():
        gpu = True
        log(f"NVIDIA GPU found: {out.stdout.strip()}")
if not gpu:
    log("No NVIDIA GPU found - installing CPU PyTorch")

if not PY.exists():
    run([sys.executable, "-m", "venv", str(VENV)])

pip = [str(PY), "-m", "pip", "install", "--progress-bar", "off", "--disable-pip-version-check"]
run(pip + ["--upgrade", "pip"])
if gpu:
    # RTX 50-series (Blackwell) needs a CUDA 12.8 build of PyTorch
    run(pip + ["torch==2.7.1", "--index-url", "https://download.pytorch.org/whl/cu128"])
else:
    run(pip + ["torch==2.7.1"])
run(pip + ["transformers==4.46.3", "pandas", "scikit-learn", "google-play-scraper==1.2.7", "tqdm",
          "fastapi", "uvicorn"])

check = ("import torch, transformers, sklearn, google_play_scraper; "
         "print('torch', torch.__version__, '| cuda', torch.cuda.is_available(), "
         "'|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'); "
         "print('transformers', transformers.__version__)")
run([str(PY), "-c", check])
log("SETUP OK")
