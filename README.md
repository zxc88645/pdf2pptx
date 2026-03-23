# PDF 抹除儀表板

前後端分離架構：後端以 **LaMa（Large Mask Inpainting）** 進行圖像抹除，並支援 PDF/PPT 匯出；前端為 **Vue 3 + Tailwind CSS** 儀表板，可載入 PDF、選擇頁面、塗抹遮罩、執行 AI 抹除，並輸出 PDF、PPT 或複製到剪貼簿。

## 需求

- **後端**：Python 3.10+、建議具備 CUDA GPU（可選，有則加速）
- **前端**：Node.js 20.19+（目前前端使用 Vite v8）

## 如何啟動

**1. 啟動後端**（在專案根目錄下開一個終端）：

```bash
cd backend
.venv\Scripts\activate        # Windows（若尚未建立虛擬環境，先執行下方「後端」建立步驟）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

看到 `Uvicorn running on http://0.0.0.0:8000` 即表示後端已就緒。

**2. 啟動前端**（再開一個終端）：

```bash
cd frontend
npm run dev
```

看到 `Local: http://localhost:5173/` 後，用瀏覽器開啟 **http://localhost:5173** 即可使用儀表板。

---

## GitHub Actions 部署

### 前端（GitHub Pages）
- 前端會在 `main` 推送後自動 build 並部署到專案頁面：`https://<user>.github.io/<repo>/`
- 後端網址可透過 GitHub Repository Variables 控制：
  - 設定 `VITE_API_BASE` 為你的後端 API 網址（例如 `https://your-backend.example.com`，不要結尾 `/`）
  - 前端會自動組合 `/api/inpaint`、`/api/export/*` 等路徑
- 需要在 GitHub 上把 Pages source 設定為「GitHub Actions」。

### 後端（GHCR 容器）
- 後端會自動建置並推送多變體映像到：`ghcr.io/<owner>/pdf2pptx-backend`
- 版本由 tag 決定：
  - 推送 `main` 時：`main-<suffix>` 與 `sha-<shortsha>-<suffix>`
  - 發佈（release）時：`<release-tag>-<suffix>`（例如 `v1.2.3-cuda12.8`）
  - 另外會提供 alias：`cpu`、`cuda12.4`、`cuda12.6`、`cuda12.8`（main/release 時更新）
- 例子（部署到你自己的伺服器）：
  - CPU：
    ```bash
    docker run -p 8000:8000 ghcr.io/<owner>/pdf2pptx-backend:cpu
    ```
  - CUDA 12.8（建議 GPU 主機搭配 `--gpus all`）：
    ```bash
    docker run --gpus all -p 8000:8000 ghcr.io/<owner>/pdf2pptx-backend:cuda12.8
    ```
- 後端可用的環境變數（見 `backend/.env.example`）：
  - `PRELOAD_LAMA`：是否在啟動時預載 LaMa 模型
  - `UPLOAD_DIR` / `OUTPUT_DIR`：暫存與輸出目錄

---

## 後端

使用 **Python 3.10+** 建立虛擬環境：

```bash
cd backend
py -3.10 -m venv .venv   # 或 py -3 使用預設 3.x
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

Windows 也可執行 `backend\scripts\setup_venv.ps1` 一鍵建立並啟用虛擬環境。

環境變數（可選，見 `backend/.env.example`）：

- `UPLOAD_DIR` / `OUTPUT_DIR`：暫存與輸出目錄
- `PDF_DPI`：PDF 轉圖 DPI，預設 200

**抹除引擎**：使用 **LaMa**（simple-lama-inpainting），無需 prompt、支援整圖一次運算，適合移除圖中物件。有 GPU 時會自動使用以加速。

啟動：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

首次呼叫 `/api/inpaint` 時會下載並載入 LaMa 模型。預設啟動時會預載模型（`PRELOAD_LAMA=1`），可避免首次請求延遲；多 worker 時建議只開 1 個以免重複佔用顯存。

### GPU 環境（本機開發）

若本機有 NVIDIA GPU，可先安裝對應 CUDA 的 PyTorch 再裝其餘依賴：

```bash
cd backend
pip uninstall torch torchvision -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

確認後端是否使用 GPU：呼叫 `GET http://localhost:8000/health`，若回傳 `"cuda_available": true` 即表示 PyTorch 已偵測到 CUDA。

### Docker（可選 GPU）

專案提供支援 CUDA 的 Dockerfile。建置與執行時可掛載 GPU：

```bash
cd backend
docker build -t pdf2pptx-backend .
docker run --gpus all -p 8000:8000 pdf2pptx-backend
```

無 GPU 時可省略 `--gpus all`，後端仍可於 CPU 運作（較慢）。可透過 `GET http://localhost:8000/health` 的 `cuda_available` 確認是否使用 GPU。

## 前端

```bash
cd frontend
npm install
npm run dev
```

預設會以 Vite proxy 將 `/api` 轉發到 `http://127.0.0.1:8000`。若後端在不同位址，可設 `VITE_API_BASE`（見 `frontend/.env.example`）。

建置：

```bash
npm run build
npm run preview  # 預覽 dist
```

## 使用流程

1. 在儀表板選擇 **PDF 檔案** 並載入。
2. 用 **頁面** 控制切換要處理的頁碼。
3. 在預覽上以滑鼠 **塗抹白色遮罩**（白色區域為要抹除處），可調整筆刷大小。
4. 點 **執行 AI 抹除**，等待後端運算後會顯示結果圖。
5. **複製到剪貼簿**：將結果圖複製；**下載 PDF**：以當前頁抹除結果替換原 PDF 該頁後下載整份 PDF；**下載 PPT**：將結果圖匯出為一頁投影片的 .pptx。

## API 摘要

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查，回傳 `cuda_available` 可確認是否使用 GPU |
| POST | `/api/inpaint` | 上傳 `image`、`mask`（multipart），回傳 PNG |
| POST | `/api/export/pdf` | 上傳多張圖片，回傳合併的 PDF |
| POST | `/api/export/pdf-from-pdf` | 上傳 `pdf`、`replace_page_index`、`mask`，回傳替換該頁後的 PDF |
| POST | `/api/export/ppt` | 上傳多張圖片，回傳每圖一頁的 .pptx |

## 專案結構

```
backend/          # FastAPI + LaMa (simple-lama-inpainting) + PyMuPDF + python-pptx
frontend/         # Vue 3 + Vite + Tailwind + PDF.js
```
