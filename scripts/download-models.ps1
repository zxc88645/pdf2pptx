# Require UTF-8 for Chinese output
# 預先下載 OCR 與 Inpaint 模型到對應的 volume 掛載點
# 執行前請在專案根目錄（與 docker-compose.yml 同層）
# 使用方式: .\scripts\download-models.ps1  或  pwsh -File scripts\download-models.ps1

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $ProjectRoot 'docker-compose.yml'))) {
    $ProjectRoot = Get-Location
}
if (-not (Test-Path (Join-Path $ProjectRoot 'docker-compose.yml'))) {
    Write-Error 'Run from project root (folder containing docker-compose.yml).'
    exit 1
}

Set-Location $ProjectRoot

# 偵測 compose 指令（Docker 或 Podman）
$ComposeCmd = $null
if (Get-Command 'docker' -ErrorAction SilentlyContinue) {
    try { $null = docker compose version 2>&1; if ($LASTEXITCODE -eq 0) { $ComposeCmd = 'docker compose' } } catch {}
}
if (-not $ComposeCmd -and (Get-Command 'podman' -ErrorAction SilentlyContinue)) {
    try { $null = podman compose version 2>&1; if ($LASTEXITCODE -eq 0) { $ComposeCmd = 'podman compose' } } catch {}
}
if (-not $ComposeCmd) {
    Write-Host 'Need docker compose or podman compose. Install Docker Desktop or Podman.' -ForegroundColor Red
    exit 1
}

$ComposeArgs = $ComposeCmd -split ' '
$ComposeExe = $ComposeArgs[0]
$ComposeSub = $ComposeArgs[1]

Write-Host ('Using: ' + $ComposeCmd) -ForegroundColor Cyan
Write-Host ''

# 1) 先建置映像（確保有最新程式與依賴）
Write-Host '[1/3] Building images...' -ForegroundColor Yellow
& $ComposeExe $ComposeSub build ocr-service inpaint-service
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 2) 下載 OCR 模型到 volume ocr-models (掛載為 /data/ocr-cache，HOME=/data/ocr-cache)
Write-Host ''
Write-Host '[2/3] Downloading PaddleOCR models to ocr-models volume...' -ForegroundColor Yellow
$ocrCode = @'
from paddleocr import PaddleOCR; PaddleOCR(device='cpu', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=True); print('OCR done')
'@
& $ComposeExe $ComposeSub run --rm -e USE_GPU=false ocr-service python -c $ocrCode
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 3) 下載 Inpaint 模型到 volume hf-cache (掛載為 /data/hf-cache，HF_HOME=/data/hf-cache)
Write-Host ''
Write-Host '[3/3] Downloading Stable Diffusion Inpaint model to hf-cache volume...' -ForegroundColor Yellow
$inpaintCode = @'
import torch; from diffusers import StableDiffusionInpaintPipeline; import os; m=os.getenv('INPAINT_MODEL_ID','runwayml/stable-diffusion-inpainting'); StableDiffusionInpaintPipeline.from_pretrained(m, torch_dtype=torch.float32, safety_checker=None); print('Inpaint done')
'@
& $ComposeExe $ComposeSub run --rm inpaint-service python -c $inpaintCode
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
$msg = 'Done. Next: ' + $ComposeCmd + ' up --build'
Write-Host $msg -ForegroundColor Green
