"""Orchestrate PDF -> PPT pipeline: split, OCR, mask, inpainting, assemble."""
import json
from pathlib import Path

from app.services.storage import (
    job_pdf_path,
    job_pages_path,
    job_masks_path,
    job_inpainted_path,
    job_output_pptx_path,
)
from app.services.job_state import update_job
from app.worker.pdf_split import split_pdf_to_pages
from app.worker.ocr import run_ocr_pages
from app.worker.mask import build_masks_for_job
from app.worker.inpainting import inpaint_all_pages
from app.worker.ppt_assembly import assemble_ppt

OCR_JSON = "ocr.json"


def run_pipeline(job_id: str) -> None:
    try:
        pdf_path = job_pdf_path(job_id)
        if not pdf_path.is_file():
            update_job(job_id, status="failed", error="PDF file not found")
            return
        pages_dir = job_pages_path(job_id)
        masks_dir = job_masks_path(job_id)
        inpainted_dir = job_inpainted_path(job_id)
        out_pptx = job_output_pptx_path(job_id)

        update_job(job_id, status="splitting", progress="Splitting PDF")
        split_pdf_to_pages(pdf_path, pages_dir)

        update_job(job_id, status="ocr", progress="Running OCR")
        ocr_by_page = run_ocr_pages(pages_dir)
        ocr_path = pages_dir / OCR_JSON
        with open(ocr_path, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in ocr_by_page.items()}, f, ensure_ascii=False)

        update_job(job_id, status="inpainting", progress="Generating masks")
        build_masks_for_job(pages_dir, ocr_by_page, masks_dir)

        update_job(job_id, status="inpainting", progress="Inpainting")
        inpaint_all_pages(pages_dir, masks_dir, inpainted_dir)

        update_job(job_id, status="assembling", progress="Assembling PPT")
        ocr_by_page_int = {int(k): v for k, v in ocr_by_page.items()}
        assemble_ppt(inpainted_dir, ocr_by_page_int, out_pptx)

        update_job(job_id, status="completed", progress="Done", output_path=str(out_pptx))
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
        raise
