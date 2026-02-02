"""OCR via PaddleOCR; returns text and bboxes per page."""
from pathlib import Path
from typing import Any

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        _ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False, use_gpu=False)
    return _ocr


def run_ocr(image_path: Path) -> list[dict[str, Any]]:
    """Run OCR on one image. Returns list of {text, bbox} where bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]."""
    ocr = get_ocr()
    result = ocr.ocr(str(image_path), cls=True)
    if not result or not result[0]:
        return []
    out = []
    for line in result[0]:
        bbox, (text, _) = line
        out.append({"text": text, "bbox": bbox})
    return out


def run_ocr_pages(pages_dir: Path) -> dict[int, list[dict[str, Any]]]:
    """Run OCR on all page_XXX.png in pages_dir. Returns {1: [...], 2: [...], ...}."""
    page_files = sorted(pages_dir.glob("page_*.png"), key=lambda p: p.name)
    result = {}
    for idx, path in enumerate(page_files, start=1):
        result[idx] = run_ocr(path)
    return result
