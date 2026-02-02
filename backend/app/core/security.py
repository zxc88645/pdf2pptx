"""PDF upload validation: MIME, magic bytes, size."""
import io
from fastapi import UploadFile, HTTPException

PDF_MAGIC = b"%PDF"
ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_EXTENSION = ".pdf"


def validate_pdf(file: UploadFile, max_bytes: int) -> bytes:
    """Read and validate PDF: content-type, magic bytes, size. Returns file content."""
    if not file.filename or not file.filename.lower().endswith(MAX_EXTENSION):
        raise HTTPException(400, "Only PDF files are allowed")
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "Content-Type must be application/pdf")
    content = b""
    while True:
        chunk = file.file.read(8192)
        if not chunk:
            break
        content += chunk
        if len(content) > max_bytes:
            raise HTTPException(413, "File too large")
    if len(content) < 4:
        raise HTTPException(400, "Invalid or empty file")
    if content[:4] != PDF_MAGIC:
        raise HTTPException(400, "File is not a valid PDF (magic bytes)")
    return content
