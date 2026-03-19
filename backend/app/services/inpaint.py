import io
import logging
import time
from pathlib import Path

from PIL import Image

# 模組級快取：同一 process 內只載入一次，不會每次 API 呼叫都重載
_lama = None
logger = logging.getLogger(__name__)


def get_lama():
    global _lama
    if _lama is None:
        try:
            from simple_lama_inpainting import SimpleLama
        except ImportError as e:
            raise RuntimeError(
                "請安裝 simple-lama-inpainting：pip install simple-lama-inpainting"
            ) from e
        t0 = time.perf_counter()
        _lama = SimpleLama()
        elapsed = time.perf_counter() - t0
        logger.info("LaMa 模型載入完成，耗時 %.2f 秒", elapsed)
    return _lama


def run_inpaint(image_path: Path, mask_path: Path) -> tuple[bytes, float]:
    """使用 LaMa 執行 inpainting，回傳 (PNG bytes, 推論秒數)。遮罩白=要抹除。"""
    t_load_start = time.perf_counter()
    init_image = Image.open(image_path).convert("RGB")
    mask_image = Image.open(mask_path).convert("L")
    orig_w, orig_h = init_image.size
    mask_w, mask_h = mask_image.size

    logger.info(
        "inpaint 載入: image %s mode=%s size=(%d,%d) | mask mode=%s size=(%d,%d)",
        image_path, init_image.mode, orig_w, orig_h, mask_image.mode, mask_w, mask_h,
    )

    # 強制以底圖尺寸為準，將 mask 縮放至與 image 一致，避免 "images do not match"
    if mask_image.size != (orig_w, orig_h):
        logger.info(
            "inpaint: mask 尺寸 (%d,%d) 與 image (%d,%d) 不一致，自動縮放 mask",
            mask_w, mask_h, orig_w, orig_h,
        )
        mask_image = mask_image.resize((orig_w, orig_h), Image.Resampling.LANCZOS)

    load_sec = time.perf_counter() - t_load_start
    logger.info(
        "inpaint 呼叫 LaMa 前: init_image.size=(%d,%d) mask_image.size=(%d,%d)",
        init_image.size[0], init_image.size[1], mask_image.size[0], mask_image.size[1],
    )

    lama = get_lama()
    t_infer_start = time.perf_counter()
    try:
        result = lama(init_image, mask_image)
    except Exception as e:
        logger.exception(
            "inpaint LaMa 呼叫例外: %s | init_image.size=%s mask_image.size=%s",
            e, init_image.size, mask_image.size,
        )
        raise
    inference_sec = time.perf_counter() - t_infer_start

    t_compose_start = time.perf_counter()
    # LaMa 可能回傳與輸入不同尺寸的 result（例如內部 pad 到 8 的倍數），需縮放回原圖尺寸再貼上
    if result.size != (orig_w, orig_h):
        logger.info(
            "inpaint: LaMa 回傳 result.size=%s，縮放回 (%d,%d) 再合成",
            result.size, orig_w, orig_h,
        )
        result = result.resize((orig_w, orig_h), Image.Resampling.LANCZOS)
    output = init_image.copy()
    output.paste(result, (0, 0), mask=mask_image)
    buf = io.BytesIO()
    # compress_level=1 明顯快於預設 6，可縮短「合成存檔」時間
    output.save(buf, format="PNG", compress_level=1)
    buf.seek(0)
    out_bytes = buf.read()
    compose_sec = time.perf_counter() - t_compose_start

    logger.info(
        "inpaint 細項: 載入圖 %.3fs | 推論 %.3fs | 合成存檔 %.3fs | 小計 %.3fs",
        load_sec, inference_sec, compose_sec, load_sec + inference_sec + compose_sec,
    )

    # 本次推論所用的 Device 
    logger.info("inpaint 使用裝置: %s", lama.device)
    
    return out_bytes, inference_sec
