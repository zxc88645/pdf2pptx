"""Convert PDF pages to images using pdf2image."""
from pathlib import Path
from typing import List

from pdf2image import convert_from_path
from PIL import Image


def pdf_to_images(pdf_path: str | Path, dpi: int = 150) -> List[Image.Image]:
    """
    Convert each PDF page to a PIL Image.

    Requires poppler (e.g. poppler-utils on Debian/Ubuntu).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    images = convert_from_path(str(path), dpi=dpi)
    return list(images)
