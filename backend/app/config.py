"""Backend configuration."""
import os

# Service URLs (Docker Compose service names when running in container)
OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://ocr-service:8001")
INPAINT_SERVICE_URL = os.getenv("INPAINT_SERVICE_URL", "http://inpaint-service:8002")

# Limits
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "10"))
MAX_IMAGES_TO_PDF = int(os.getenv("MAX_IMAGES_TO_PDF", "50"))

# Timeouts (seconds)
# Inpaint on CPU can be slow; allow longer than default requests timeout.
INPAINT_TIMEOUT = int(os.getenv("INPAINT_TIMEOUT", "300"))

# PPT text font (思源黑體)
FONT_NAME = os.getenv("PPT_FONT_NAME", "Source Han Sans TC")
# Font file path for future embedding (Phase 2)
FONT_PATH = os.getenv("PPT_FONT_PATH", "")
# 字體大小係數（bbox 高度 → pt）：OCR bbox 往往偏大，預設 0.55 可減少跑版
FONT_SIZE_FACTOR = float(os.getenv("PPT_FONT_SIZE_FACTOR", "0.55"))
