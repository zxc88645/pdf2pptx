"""Generate inpainting mask from OCR bboxes: text regions = white (255), rest = black (0)."""
from pathlib import Path
import numpy as np
from PIL import Image


def bbox_to_mask_shape(bbox: list, width: int, height: int) -> tuple[int, int, int, int]:
    """Convert OCR bbox [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] to (x, y, w, h) with padding."""
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    x1 = max(0, int(min(xs)) - 2)
    y1 = max(0, int(min(ys)) - 2)
    x2 = min(width, int(max(xs)) + 2)
    y2 = min(height, int(max(ys)) + 2)
    return x1, y1, x2 - x1, y2 - y1


def build_mask(image_path: Path, ocr_results: list[dict], out_path: Path) -> None:
    """Create mask image: white (255) where text is, black (0) elsewhere."""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    mask = np.zeros((h, w), dtype=np.uint8)
    for item in ocr_results:
        bbox = item.get("bbox", [])
        if len(bbox) < 4:
            continue
        x, y, bw, bh = bbox_to_mask_shape(bbox, w, h)
        if bw > 0 and bh > 0:
            mask[y : y + bh, x : x + bw] = 255
    Image.fromarray(mask).save(out_path)


def build_masks_for_job(pages_dir: Path, ocr_by_page: dict[int, list], masks_dir: Path) -> list[Path]:
    """Build mask for each page. pages_dir has page_001.png etc.; ocr_by_page is {1: [...], ...}."""
    masks_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for page_num, ocr_list in ocr_by_page.items():
        img_name = f"page_{page_num:03d}.png"
        img_path = pages_dir / img_name
        if not img_path.exists():
            continue
        out_path = masks_dir / img_name
        build_mask(img_path, ocr_list, out_path)
        paths.append(out_path)
    return paths
