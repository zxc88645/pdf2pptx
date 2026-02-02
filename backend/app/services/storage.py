"""Storage paths and file operations under STORAGE_DIR."""
import uuid
from pathlib import Path
from app.core.config import (
    UPLOADS_DIR,
    PAGES_DIR,
    MASKS_DIR,
    INPAINTED_DIR,
    OUTPUT_DIR,
)


def make_job_id() -> str:
    return uuid.uuid4().hex


def job_upload_path(job_id: str) -> Path:
    return UPLOADS_DIR / job_id


def job_pdf_path(job_id: str) -> Path:
    return job_upload_path(job_id) / "document.pdf"


def job_pages_path(job_id: str) -> Path:
    return PAGES_DIR / job_id


def job_masks_path(job_id: str) -> Path:
    return MASKS_DIR / job_id


def job_inpainted_path(job_id: str) -> Path:
    return INPAINTED_DIR / job_id


def job_output_path(job_id: str) -> Path:
    return OUTPUT_DIR / job_id


def job_output_pptx_path(job_id: str) -> Path:
    return job_output_path(job_id) / "output.pptx"


def ensure_dirs() -> None:
    for d in (UPLOADS_DIR, PAGES_DIR, MASKS_DIR, INPAINTED_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)
