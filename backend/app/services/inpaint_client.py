"""Client for Inpaint service (Stable Diffusion / LaMa Inpainting)."""
import io
from typing import Optional

import requests
from PIL import Image

from app.config import INPAINT_SERVICE_URL, INPAINT_TIMEOUT


def run_inpaint(image: Image.Image, mask: Image.Image, backend: Optional[str] = None) -> Image.Image:
    """
    Send image and mask to inpaint service; mask: text region = 255, background = 0.
    Returns inpainted image as PIL Image.
    """
    img_buf = io.BytesIO()
    image.save(img_buf, format="PNG")
    img_buf.seek(0)
    mask_buf = io.BytesIO()
    mask.save(mask_buf, format="PNG")
    mask_buf.seek(0)
    files = {
        "image": ("image.png", img_buf, "image/png"),
        "mask": ("mask.png", mask_buf, "image/png"),
    }
    params = None
    if backend:
        params = {"backend": backend}
    # Inpaint can be slow on CPU, especially for多頁、大圖 PDF。
    # Timeout 可透過 INPAINT_TIMEOUT 環境變數調整，預設 300 秒。
    resp = requests.post(
        f"{INPAINT_SERVICE_URL}/inpaint",
        files=files,
        params=params,
        timeout=INPAINT_TIMEOUT,
    )
    resp.raise_for_status()
    out = Image.open(io.BytesIO(resp.content))
    return out.convert("RGB")
