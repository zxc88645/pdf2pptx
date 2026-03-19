import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent

_def_upload = str(_BASE / "uploads")
_def_output = str(_BASE / "outputs")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", _def_upload))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", _def_output))

# PDF 轉圖 DPI（愈高愈清晰，預設 72 DPI）
PDF_DPI = int(os.getenv("PDF_DPI", "72"))

# 確保目錄存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
