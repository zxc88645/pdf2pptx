# PDF 圖像轉可編輯 PPT（POC）

前後端分離的網頁系統：將「不可編輯的純圖 PDF」轉成「結構清楚、文字可編輯的 PPT」。

## 架構

- **frontend**：Vue 3 + Vite（Node 24），上傳 PDF、下載 PPT
- **backend**：FastAPI，主流程、PDF→圖、呼叫 OCR/Inpaint、組裝 PPT
- **ocr-service**：PaddleOCR，文字偵測與辨識（可選 GPU）
- **inpaint-service**：Stable Diffusion Inpainting，去除圖片中的文字像素

## 環境需求

- Podman（建議 4.1+，內建 Compose）
- （可選）NVIDIA GPU + [nvidia-container-toolkit for Podman](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-on-rhel-centos-7-8)，供 OCR / Inpaint 加速

## 預先下載模型（可選）

若希望先將 OCR 與 Inpaint 模型下載到對應 volume，再啟動服務，可執行：

- **Windows（PowerShell）**：在專案根目錄執行  
  `.\scripts\download-models.ps1`
- **Linux / macOS / WSL**：在專案根目錄執行  
  `./scripts/download-models.sh`

需已安裝並在 PATH 中可用的 `docker compose` 或 `podman compose`。下載完成後，之後執行 `podman compose up --build` 會直接使用快取，不需重複下載。

## 思源黑體字體（可選）

PDF 轉 PPT 時，文字會使用思源黑體。若系統未安裝，PowerPoint 會以其他字體取代。建議執行下載腳本：

- **Windows（PowerShell）**：`.\scripts\download-font.ps1`
- **Linux / macOS / WSL**：`./scripts/download-font.sh`

字體會下載至 `fonts/` 目錄，請依腳本提示安裝（例如雙擊字體檔或複製到系統字體目錄）。

## 啟動方式

```bash
podman compose up --build
```
（預設使用 CPU）

如要啟用 GPU（需已安裝 NVIDIA 驅動與 nvidia-container-toolkit for Podman）：

```bash
# Podman 需額外加上 docker-compose.podman-gpu.yml，才能把 GPU 傳進容器
podman compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.podman-gpu.yml up --build
```

若使用舊版 Podman 或獨立 `podman-compose`，可改為：

```bash
podman-compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.podman-gpu.yml up --build
```

> 💡 **詳細的 Docker/Podman Compose CPU & GPU 部署指南**，請參考 [DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md) 或 [PODMAN_GUIDE.md](PODMAN_GUIDE.md)

啟動後：

- **前端**：<http://localhost:5173>（Vue + Vite，Node 24，/api 代理至 backend）
- **API 文件**：<http://localhost:8000/docs>
- **健康檢查**：<http://localhost:8000/health>

前端已包含在 compose 中，上傳 PDF 後可下載 `output.pptx`。若要在本機跑前端開發（需先啟動上述服務），可 `cd frontend && npm install && npm run dev`。

## 專案結構

```
pdf2pptx/
├── backend/          # FastAPI、pdf2image、python-pptx
├── ocr-service/      # PaddleOCR
├── inpaint-service/  # Diffusers Inpainting
├── frontend/         # Vue 3 + Vite（Node 24，含 Dockerfile）
├── docker-compose.gpu.yml  # GPU 覆寫設定（啟用 GPU 時一起帶上）
├── scripts/          # 模型預下載腳本 download-models.ps1 / download-models.sh
├── docker-compose.yml
├── .env.example
└── README.md
```

## API（POC）

- `GET /health`：健康檢查
- `POST /convert`：`form-data` 欄位 `file`（PDF），回傳 `output.pptx` 附件

## 注意事項

- POC 限制：單次轉換最多 10 頁（可透過 `MAX_PDF_PAGES` 調整）。
- OCR / Inpaint 預設使用 CPU。啟用 GPU 時使用 `docker-compose.gpu.yml`，會自動讓 ocr-service（Dockerfile.gpu + paddlepaddle-gpu）與 inpaint-service（Dockerfile.gpu + CUDA）皆使用 GPU。
- **ocr-service GPU**：預設 Dockerfile.gpu 支援 RTX 50 系列 (sm_120)。若使用 RTX 30/40 等舊款 GPU，可改 `dockerfile: Dockerfile.gpu.legacy`。
- Inpaint 模型較大，首次啟動會下載，耗時較長。
- **模型僅下載一次**：OCR 與 Inpaint 的模型分別寫入 named volume `ocr-models`、`hf-cache`，之後重新部署（`podman compose up --build`）會沿用既有快取，不會重複下載。可先執行 `scripts/download-models.ps1`（Windows）或 `scripts/download-models.sh`（Linux/macOS）預先下載到對應掛載點。若要強制重新下載，可先刪除 volume：`podman volume rm pdf2pptx_ocr-models pdf2pptx_hf-cache`。
