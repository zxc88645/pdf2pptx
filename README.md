## LaMa Inpainting Studio

一個使用 **Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia** 開發的前端單頁應用，
在瀏覽器端透過 **onnxruntime-web** 載入 `migan_pipeline_v2.onnx` 模型，實現「塗抹遮罩 → 圖像抹除（inpainting）」的互動工具。

### 功能概覽

- **圖片選擇**：從本機選擇圖片（不會上傳到伺服器）。
- **遮罩塗抹**：在畫布上用筆刷塗抹想要抹除的區域（白色遮罩）。
- **前端推理**：在瀏覽器使用 `onnxruntime-web` 載入 `public/models/migan_pipeline_v2.onnx` 進行推理。
- **結果預覽**：支援「原圖 / 結果」切換查看抹除效果。

### 專案結構（重點）

- `index.html`：Vite 入口 HTML。
- `package.json`：專案依賴與腳本。
- `tailwind.config.cjs`、`postcss.config.cjs`：Tailwind 4 與 PostCSS 設定。
- `public/models/migan_pipeline_v2.onnx`：MiGAN 圖像抹除模型。
- `src/main.ts`：建立 Vue App，註冊 Pinia、載入 Tailwind 樣式。
- `src/App.vue`：主版面（左側編輯與遮罩、右側結果預覽）。
- `src/stores/useEditorStore.ts`：圖片、推理狀態與錯誤訊息的 Pinia store。
- `src/services/inferenceService.ts`：封裝 `onnxruntime-web`，負責載入 LaMa 模型與執行 inpainting 推理。
- `src/utils/image.ts`：影像處理工具（載入、縮放、ImageData <-> DataURL）。
- `src/utils/tensor.ts`：ImageData 與 ONNX Tensor 之間的轉換。
- `src/components/editor/*`：
  - `ImageUploader.vue`：圖片選擇元件。
  - `CanvasEditor.vue`：顯示圖片與塗抹遮罩的畫布。
  - `Toolbar.vue`：執行推理 / 清除遮罩按鈕。
  - `ResultPanel.vue`：原圖與結果的對比預覽。

### 開發與執行

1. 安裝依賴

   ```bash
   npm install
   ```

2. 開發模式（預設在 `http://localhost:5173`）

   ```bash
   npm run dev
   ```

3. 產生正式版

   ```bash
   npm run build
   npm run preview
   ```

### 使用說明

1. 進入頁面後，先在左側「選擇圖片」按鈕選一張本機圖片。
2. 在中間畫布上，用滑鼠左鍵拖曳塗抹要抹除的區域（白色遮罩）。
3. 點擊「執行抹除」，前端會載入 `migan_pipeline_v2.onnx` 並執行推理。
4. 右側「結果預覽」可以在「原圖 / 結果」間切換比較差異。

> 注意：
> - 模型檔位於 `public/models/migan_pipeline_v2.onnx`，如需更換模型名稱或路徑，需同時更新 `src/services/inferenceService.ts` 中的 `DEFAULT_MODEL_URL`。
> - 推理全部在瀏覽器端進行，圖片不會傳到後端伺服器。
