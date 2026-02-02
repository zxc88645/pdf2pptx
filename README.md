# PDF → 可編輯 PPT 智能轉換系統

將純圖檔 PDF（掃描、設計輸出）轉換為文字可編輯的 PowerPoint 簡報。系統採前後端分離，Docker 一鍵部署，支援 GPU Worker 擴充。

## 架構

- **Frontend**：Vue 3 + Vite，靜態由 Nginx 提供
- **API**：FastAPI，負責上傳、任務狀態、下載
- **Worker**：Celery，執行 PDF 拆頁 → OCR → 去字 (Inpainting) → PPT 組裝
- **Redis**：任務佇列與狀態

## 本地開發

### 後端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

需先啟動 Redis（例如本機 `redis-server`，或容器：`docker run -d -p 6379:6379 redis:7-alpine` / `podman run -d -p 6379:6379 redis:7-alpine`）。

```bash
# 終端 1：API
set REDIS_URL=redis://localhost:6379/0
set STORAGE_DIR=%cd%\data
mkdir data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 終端 2：Worker（需安裝 PaddleOCR、Diffusers 等，耗時與資源較大）
set REDIS_URL=redis://localhost:6379/0
set STORAGE_DIR=%cd%\data
celery -A app.worker.celery_app worker -l info
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

開發時 Vite 會把 `/api` 代理到 `http://localhost:8000`，無需改 Nginx。

## 容器部署（Docker / Podman）

### 建置與啟動

**Docker：**
```bash
docker compose build
docker compose up -d
```

**Podman：**
```bash
podman compose build
podman compose up -d
```

- 首次建置會下載 PyTorch、PaddlePaddle、Diffusers 等大型依賴，約需 15–30 分鐘。
- **Build 優化**：啟用 BuildKit 可重用 pip/npm 快取，加快重複建置。  
  - Docker：`$env:DOCKER_BUILDKIT=1`（PowerShell）或 `export DOCKER_BUILDKIT=1`（Bash）後再 `docker compose build`。  
  - Podman：`podman compose build` 若支援 cache mount 會自動使用。  
- **依賴分層**：backend 使用 `requirements-base.txt`（輕量）與 `requirements-ml.txt`（笨重）。**只改 `requirements-ml.txt`** 時，base 層可沿用快取，略省時間；**改 `requirements-base.txt` 或任一檔** 仍會重跑後續層，整體 rebuild 還是會久。本地開發仍用單一 `pip install -r requirements.txt` 即可。
- API 與 Worker 共用同一 backend 映像，只需建置一次。
- 前端：<http://localhost:80>
- 上傳 PDF 後由 Worker 處理，完成後可下載 PPT。

### GPU Worker（可選）

需安裝 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)（Docker）或 Podman 的 [GPU 支援](https://docs.podman.io/en/stable/markdown/podman-run.1.html#option-gpu)。

**Docker：**
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

**Podman：**
```bash
podman compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Worker 會使用 GPU 跑 Inpainting，加快去字步驟。

## 環境變數

| 變數 | 說明 | 預設 |
|------|------|------|
| `STORAGE_DIR` | 儲存根目錄 | `/data` |
| `REDIS_URL` | Redis 連線 | `redis://redis:6379/0` |
| `MAX_UPLOAD_BYTES` | 上傳大小上限（bytes） | `52428800`（50MB） |
| `JOB_TTL_SECONDS` | 任務狀態 TTL | `86400`（24h） |
| `HF_HOME` / `HF_CACHE_DIR` | Hugging Face 模型快取 | `STORAGE_DIR/.hf` |

## 儲存目錄結構

在 `STORAGE_DIR` 下：

```
/data
├── uploads/{job_id}/     # 上傳的 PDF
├── pages/{job_id}/       # 拆頁圖片、OCR 結果
├── masks/{job_id}/       # 文字區域 mask
├── inpainted/{job_id}/    # 去字後圖片
├── output/{job_id}/      # 產出 PPT
└── .hf/                  # 模型快取（Diffusers）
```

## 安全性

- 容器內以非 root 執行（backend 透過 entrypoint 以 gosu 降權）
- `no-new-privileges` 已開啟
- 前端容器唯讀
- 上傳僅允許 PDF，並以 magic bytes 驗證；大小受 `MAX_UPLOAD_BYTES` 與 Nginx `client_max_body_size` 限制

## 依賴說明

- **PaddleOCR**：需 PaddlePaddle（CPU/GPU）。若使用 PaddleOCR 3.x，請依官方文件安裝 PaddlePaddle 3.x。
- **Diffusers Inpainting**：首次執行會下載 Stable Diffusion Inpainting 模型，建議使用 GPU 與足夠磁碟空間；模型可透過 `STORAGE_DIR/.hf` 共用。

## 授權

專案內部使用，未標明授權者以專案擁有者為準。
