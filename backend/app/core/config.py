"""Application configuration from environment."""
import os
from pathlib import Path

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/data"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "52428800"))  # 50MB
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "86400"))  # 24h
API_PREFIX = "/api"

# Subdirs under STORAGE_DIR
UPLOADS_DIR = STORAGE_DIR / "uploads"
PAGES_DIR = STORAGE_DIR / "pages"
MASKS_DIR = STORAGE_DIR / "masks"
INPAINTED_DIR = STORAGE_DIR / "inpainted"
OUTPUT_DIR = STORAGE_DIR / "output"
HF_CACHE_DIR = STORAGE_DIR / ".hf"
