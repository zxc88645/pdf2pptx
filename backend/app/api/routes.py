"""API routes: jobs upload, status, download."""
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import API_PREFIX, MAX_UPLOAD_BYTES
from app.core.security import validate_pdf
from app.models.schemas import JobCreateResponse, JobResponse
from app.services.storage import make_job_id, job_upload_path, job_pdf_path, job_output_pptx_path, ensure_dirs
from app.services.job_state import set_job, get_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse)
async def create_job(file: UploadFile):
    ensure_dirs()
    content = validate_pdf(file, MAX_UPLOAD_BYTES)
    job_id = make_job_id()
    upload_dir = job_upload_path(job_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = job_pdf_path(job_id)
    pdf_path.write_bytes(content)
    set_job(job_id, "pending")
    from app.worker.celery_app import run_pipeline_task
    run_pipeline_task.delay(job_id)
    return JobCreateResponse(job_id=job_id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    data = get_job(job_id)
    if not data:
        raise HTTPException(404, "Job not found")
    base_url = ""  # Frontend will use relative path
    download_url = None
    if data.get("status") == "completed" and data.get("output_path"):
        download_url = f"{base_url}/api/jobs/{job_id}/download"
    return JobResponse(
        job_id=job_id,
        status=data["status"],
        progress=data.get("progress") or None,
        error=data.get("error") or None,
        download_url=download_url,
    )


@router.get("/{job_id}/download")
async def download_job(job_id: str):
    data = get_job(job_id)
    if not data:
        raise HTTPException(404, "Job not found")
    if data.get("status") != "completed":
        raise HTTPException(400, "Job not completed yet")
    path = job_output_pptx_path(job_id)
    if not path.is_file():
        raise HTTPException(404, "Output file not found")
    return FileResponse(
        path,
        filename="output.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
