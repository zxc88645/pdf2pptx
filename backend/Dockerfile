# 後端映像：LaMa inpainting，可選 GPU（--gpus all）
# 使用 build args 產出 cpu / cuda12.4 / cuda12.6 / cuda12.8 等多版本映像。
ARG BASE_IMAGE=nvidia/cuda:12.8-runtime-ubuntu22.04
FROM ${BASE_IMAGE}

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir torch torchvision --index-url ${TORCH_INDEX_URL} \
    && pip install --no-cache-dir -r requirements.txt
COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
