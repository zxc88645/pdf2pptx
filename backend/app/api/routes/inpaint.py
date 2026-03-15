import logging
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import Response

from app.services.inpaint import run_inpaint

router = APIRouter(prefix="/api", tags=["inpaint"])
logger = logging.getLogger(__name__)


@router.post("/inpaint")
async def inpaint(image: UploadFile = File(...), mask: UploadFile = File(...)):
    """上傳 image 與 mask（白=要抹除區域），回傳 PNG 圖像 bytes。推論時間在 response header X-Inference-Time-Sec。"""
    t_req_start = time.perf_counter()
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "image 必須為圖片檔")
    if not mask.content_type or not mask.content_type.startswith("image/"):
        raise HTTPException(400, "mask 必須為圖片檔")

    t_upload_start = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        img_path = tmp_path / "image.png"
        msk_path = tmp_path / "mask.png"
        content = await image.read()
        img_path.write_bytes(content)
        content = await mask.read()
        msk_path.write_bytes(content)
        upload_sec = time.perf_counter() - t_upload_start

        t_run_start = time.perf_counter()
        try:
            png_bytes, inference_sec = run_inpaint(img_path, msk_path)
        except Exception as e:
            raise HTTPException(500, f"Inpainting 失敗: {str(e)}")
        run_sec = time.perf_counter() - t_run_start

    total_sec = time.perf_counter() - t_req_start
    logger.info(
        "inpaint 請求: 收檔+暫存 %.3fs | run_inpaint %.3fs（含推論 %.3fs）| 總計 %.3fs",
        upload_sec, run_sec, inference_sec, total_sec,
    )
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "X-Inference-Time-Sec": f"{inference_sec:.3f}",
            "X-Request-Total-Sec": f"{total_sec:.3f}",
        },
    )
