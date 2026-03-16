"""Client for OCR service (PaddleOCR)."""
import io
from typing import Any, List

import requests
from PIL import Image

from app.config import OCR_SERVICE_URL


def run_ocr(image: Image.Image, min_score: float | None = None) -> List[dict[str, Any]]:
    """
    Send a single image to OCR service and return results.

    Each result: {"bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], "text": "...", "confidence": float}
    Backend may normalize bbox to [x1,y1,x2,y2] as needed.
    """
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    files = {"image": ("page.png", buf, "image/png")}
    params: dict[str, Any] = {}
    if min_score is not None:
        params["min_score"] = float(min_score)
    resp = requests.post(f"{OCR_SERVICE_URL}/ocr", params=params, files=files, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])
