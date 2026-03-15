import logging
import os
import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import inpaint, export

# 讓 app 內 logger.info 會輸出（預設可能只顯示 WARNING 以上）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("app").setLevel(logging.INFO)

app = FastAPI(title="PDF 抹除 API", version="0.1.0")


@app.on_event("startup")
def startup_preload_lama():
    """啟動時預載 LaMa，避免首次 /api/inpaint 才載入導致延遲。可設 PRELOAD_LAMA=0 關閉。"""
    if os.getenv("PRELOAD_LAMA", "1").strip().lower() in ("0", "false", "no"):
        return
    try:
        from app.services.inpaint import get_lama
        get_lama()
    except Exception:
        pass  # 首次請求時再載入即可


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inpaint.router)
app.include_router(export.router)


@app.get("/health")
def health():
    return {"status": "ok", "cuda_available": torch.cuda.is_available()}
