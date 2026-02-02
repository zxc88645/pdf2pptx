"""Request/response schemas."""
from pydantic import BaseModel
from typing import Optional


class JobCreateResponse(BaseModel):
    job_id: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[str] = None
    error: Optional[str] = None
    download_url: Optional[str] = None
