"""Build binary mask from OCR bbox list (text region = 255, background = 0)."""
from typing import Any, List

from PIL import Image
import numpy as np


def _bbox_to_rect(bbox: Any) -> tuple[int, int, int, int]:
    """Return (x1, y1, x2, y2) in pixel coordinates."""
    if isinstance(bbox[0], (list, tuple)):
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        return (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
    return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))


def draw_mask(
    width: int,
    height: int,
    results: List[dict],
    padding: int = 4,
) -> Image.Image:
    """
    Create a binary mask image: text regions = 255, background = 0.
    results: list of {"bbox": ...} from OCR.
    padding: expand each bbox by this many pixels so mask covers full character area (default 4).
    """
    arr = np.zeros((height, width), dtype=np.uint8)
    pad = max(0, padding)
    for item in results:
        bbox = item.get("bbox")
        if not bbox:
            continue
        x1, y1, x2, y2 = _bbox_to_rect(bbox)
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(width, x2 + pad)
        y2 = min(height, y2 + pad)
        if x2 > x1 and y2 > y1:
            arr[y1:y2, x1:x2] = 255
    return Image.fromarray(arr, mode="L")
