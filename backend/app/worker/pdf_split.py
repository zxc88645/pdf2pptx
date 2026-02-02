"""PDF to per-page images."""
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

DPI = 150  # Consistent DPI for OCR and PPT coordinate mapping


def split_pdf_to_pages(pdf_path: Path, out_dir: Path) -> list[Path]:
    """Render each PDF page to PNG under out_dir. Returns list of image paths."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required; install with: pip install PyMuPDF")
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    paths = []
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(DPI / 72, DPI / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_path = out_dir / f"page_{i + 1:03d}.png"
        pix.save(str(out_path))
        paths.append(out_path)
    doc.close()
    return paths
