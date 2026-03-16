#!/usr/bin/env bash
# 預先下載 OCR 與 Inpaint 模型到對應的 volume 掛載點
# 執行前請在專案根目錄（與 docker-compose.yml 同層）
# 使用方式: ./scripts/download-models.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
  PROJECT_ROOT="$(pwd)"
fi
if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
  echo "請在專案根目錄執行，或於 pdf2pptx 目錄下執行。"
  exit 1
fi
cd "$PROJECT_ROOT"

# 偵測 compose 指令（Docker 或 Podman）
COMPOSE_CMD=""
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then
  COMPOSE_CMD="podman compose"
fi
if [ -z "$COMPOSE_CMD" ]; then
  echo "未找到 'docker compose' 或 'podman compose'，請先安裝其一。"
  exit 1
fi

echo "使用: $COMPOSE_CMD"
echo ""

echo "[1/3] 建置映像..."
$COMPOSE_CMD build ocr-service inpaint-service

echo ""
echo "[2/3] 下載 PaddleOCR 模型到 ocr-models volume（僅首次較久）..."
$COMPOSE_CMD run --rm -e USE_GPU=false ocr-service python -c \
  "from paddleocr import PaddleOCR; PaddleOCR(device='cpu', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=True); print('OCR 模型下載完成')"

echo ""
echo "[3/3] 下載 Stable Diffusion Inpainting 模型到 hf-cache volume（僅首次較久）..."
$COMPOSE_CMD run --rm inpaint-service python -c \
  "import torch; from diffusers import StableDiffusionInpaintPipeline; import os; m=os.getenv('INPAINT_MODEL_ID','runwayml/stable-diffusion-inpainting'); StableDiffusionInpaintPipeline.from_pretrained(m, torch_dtype=torch.float32, safety_checker=None); print('Inpaint 模型下載完成')"

echo ""
echo "全部模型已下載至對應 volume，之後執行 $COMPOSE_CMD up --build 將直接使用快取。"
