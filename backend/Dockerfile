# syntax=docker/dockerfile:1
# Enable BuildKit for cache mounts: DOCKER_BUILDKIT=1 or podman build
FROM python:3.11-slim

RUN groupadd -g 1000 app && useradd -u 1000 -g app -m app
WORKDIR /app

# System deps: gosu, OpenGL (PaddleOCR/OpenCV need libGL.so.1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 分兩層：只改 requirements-ml.txt 時，base 層可沿用快取
COPY requirements-base.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements-base.txt

COPY requirements-ml.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements-ml.txt

COPY . .
ENV PYTHONPATH=/app
ENV STORAGE_DIR=/data

RUN chown -R app:app /app
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
# CMD runs as app via gosu in entrypoint
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
