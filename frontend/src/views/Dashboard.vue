<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount, onMounted } from 'vue'
import PdfViewer from '../components/PdfViewer.vue'
import PdfPageThumbnails from '../components/PdfPageThumbnails.vue'
import MaskCanvas from '../components/MaskCanvas.vue'
import ExportButtons from '../components/ExportButtons.vue'
import { usePdfInpaintStore } from '../stores/pdfInpaint'
import { useToast } from '../composables/useToast'
import { inpaint } from '../api/inpaint'
import { exportPdfFull, exportPptFull, exportPngZipFull } from '../api/export'

const store = usePdfInpaintStore()
const toast = useToast()

const pdfFile = ref(null)
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(2)
const brushSize = ref(24)
const canvasSize = ref({ width: 0, height: 0 })
const pageImageBlob = ref(null)
const resultImageUrl = ref('') // object URL for 抹除結果區
const appliedImageUrl = ref('') // object URL for 預覽區已套用圖
const inpaintLoading = ref(false)
const inpaintError = ref('')
const pdfViewerRef = ref(null)
const maskCanvasRef = ref(null)
const fileInputRef = ref(null)
const isDragging = ref(false)

/** 目前頁面的抹除結果（來自 store，換頁後仍保留） */
const resultImageBlob = computed(() => store.getResult(currentPage.value))
/** 目前頁面已套用的底圖（來自 store，換頁後仍保留） */
const appliedImageBlob = computed(() => store.getApplied(currentPage.value))

// 預覽區縮放：讓用戶放大處理細節
const PREVIEW_ZOOM_MIN = 0.5
const PREVIEW_ZOOM_MAX = 3
const PREVIEW_ZOOM_STEP = 0.25
const previewZoom = ref(1)
const previewViewportSize = ref({ width: 0, height: 0 })
const previewContainerRef = ref(null)
let resizeObserver = null

function setPreviewZoom(value) {
  previewZoom.value = Math.max(PREVIEW_ZOOM_MIN, Math.min(PREVIEW_ZOOM_MAX, value))
}

function zoomIn() {
  setPreviewZoom(previewZoom.value + PREVIEW_ZOOM_STEP)
}

function zoomOut() {
  setPreviewZoom(previewZoom.value - PREVIEW_ZOOM_STEP)
}

function zoomReset() {
  previewZoom.value = 1
}

watch(resultImageBlob, (blob) => {
  if (resultImageUrl.value) URL.revokeObjectURL(resultImageUrl.value)
  resultImageUrl.value = blob ? URL.createObjectURL(blob) : ''
}, { immediate: true })

watch(appliedImageBlob, (blob) => {
  if (appliedImageUrl.value) URL.revokeObjectURL(appliedImageUrl.value)
  appliedImageUrl.value = blob ? URL.createObjectURL(blob) : ''
}, { immediate: true })

// 更換 PDF 時清空 store 與預覽相關狀態，避免與新檔混淆
watch(pdfFile, () => {
  store.clearAll()
  pageImageBlob.value = null
  canvasSize.value = { width: 0, height: 0 }
})

function updatePreviewViewportSize() {
  const el = previewContainerRef.value
  if (!el) return
  const w = el.clientWidth
  const h = el.clientHeight
  if (w > 0 && h > 0) {
    previewViewportSize.value = { width: w, height: h }
  }
}

onMounted(() => {
  resizeObserver = new ResizeObserver(updatePreviewViewportSize)
  if (previewContainerRef.value) resizeObserver.observe(previewContainerRef.value)
  nextTick(() => updatePreviewViewportSize())
})

onBeforeUnmount(() => {
  if (resultImageUrl.value) URL.revokeObjectURL(resultImageUrl.value)
  if (appliedImageUrl.value) URL.revokeObjectURL(appliedImageUrl.value)
  if (resizeObserver && previewContainerRef.value) {
    resizeObserver.disconnect()
  }
})

const currentPageIndex = computed(() => Math.max(0, currentPage.value - 1))

function onTotalPages(n) {
  totalPages.value = n
  if (currentPage.value > n) currentPage.value = 1
}

function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (file && file.type === 'application/pdf') {
    pdfFile.value = file
    currentPage.value = 1
  }
  e.target.value = ''
}

function onFileDrop(e) {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  if (file.type !== 'application/pdf') {
    toast.error('請拖放 PDF 檔案')
    return
  }
  pdfFile.value = file
  currentPage.value = 1
  toast.success('已載入 PDF')
}

function onDragOver(e) {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'copy'
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onPageImage(blob) {
  pageImageBlob.value = blob
}

/** 目前預覽／抹除使用的底圖：有套用過則用 store 內該頁的套用結果，否則用 PDF 頁面圖 */
const effectivePageBlob = computed(() => appliedImageBlob.value || pageImageBlob.value)

/** 畫布尺寸：有已套用圖時用 store 該頁儲存的尺寸，否則用 PdfViewer 即時回傳的 canvasSize */
const effectiveCanvasSize = computed(() => {
  if (appliedImageBlob.value) {
    const dim = store.getDimensions(currentPage.value)
    if (dim) return dim
  }
  return canvasSize.value
})

function onDimensions(w, h) {
  canvasSize.value = { width: w, height: h }
  store.setDimensions(currentPage.value, w, h)
}

async function runInpaint() {
  const base = effectivePageBlob.value
  if (!base) {
    inpaintError.value = '請先載入 PDF 並選擇頁面'
    return
  }
  const t0 = performance.now()
  const mask = await maskCanvasRef.value?.getMaskBlob()
  const getMaskMs = Math.round(performance.now() - t0)
  if (import.meta.env.DEV && getMaskMs > 0) {
    console.log(`[inpaint] 取得遮罩 blob: ${getMaskMs} ms`)
  }
  if (!mask) {
    inpaintError.value = '請在預覽上塗抹要抹除的區域（白色遮罩）'
    return
  }
  inpaintLoading.value = true
  inpaintError.value = ''
  const t1 = performance.now()
  try {
    const blob = await inpaint(base, mask)
    store.setResult(currentPage.value, blob)
    toast.success('AI 抹除完成')
    if (import.meta.env.DEV) {
      const apiMs = Math.round(performance.now() - t1)
      const totalMs = Math.round(performance.now() - t0)
      console.log(`[inpaint] API 請求: ${apiMs} ms | 按鈕到完成總計: ${totalMs} ms`)
    }
  } catch (e) {
    inpaintError.value = e.message || String(e)
    toast.error(e.message || String(e))
  } finally {
    inpaintLoading.value = false
  }
}

function clearMask() {
  maskCanvasRef.value?.clearMask()
}

/** 套用抹除結果：寫入 store，該頁預覽底圖改為結果圖，換頁後再回來仍保留 */
function applyResult() {
  const blob = resultImageBlob.value
  if (!blob) return
  store.setApplied(currentPage.value, blob)
  clearMask()
  toast.success('已套用')
}

// 供 ExportButtons：目前頁面有結果則用該 blob，多頁時可改為依 store.pageNumbersWithContent 彙總
const allPageBlobs = computed(() =>
  resultImageBlob.value ? [resultImageBlob.value] : []
)

/** 供 ExportButtons 取得當前遮罩 Blob（在 script 內使用 Promise 避免模板 scope 無 Promise） */
function getMaskBlobForExport() {
  return maskCanvasRef.value?.getMaskBlob?.() ?? Promise.resolve(null)
}

/** 左側下載用：完整頁面替換表 (0-based 索引 → Blob)，僅包含有修改過的頁 */
const fullExportReplacements = computed(() => {
  const out = {}
  for (const pageNum of store.pageNumbersWithContent) {
    const blob = store.getApplied(pageNum) || store.getResult(pageNum)
    if (blob) out[pageNum - 1] = blob
  }
  return out
})

const sidebarExporting = ref('') // 'pdf' | 'ppt' | ''
const sidebarMessage = ref('')

async function sidebarDownloadPdf() {
  if (!pdfFile.value || totalPages.value === 0) {
    sidebarMessage.value = '請先載入 PDF'
    return
  }
  sidebarExporting.value = 'pdf'
  sidebarMessage.value = ''
  try {
    const blob = await exportPdfFull(pdfFile.value, fullExportReplacements.value)
    const url = URL.createObjectURL(blob)
    // 快速網頁檢視：在新分頁開啟，由瀏覽器內建 PDF 檢視器顯示
    window.open(url, '_blank')
    const a = document.createElement('a')
    a.href = url
    a.download = 'output.pdf'
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 15000)
    sidebarMessage.value = 'PDF 已下載並於新分頁開啟'
    toast.success('PDF 已下載')
  } catch (e) {
    sidebarMessage.value = '下載 PDF 失敗: ' + (e.message || String(e))
    toast.error('下載 PDF 失敗: ' + (e.message || String(e)))
  } finally {
    sidebarExporting.value = ''
  }
}

async function sidebarDownloadPpt() {
  if (!pdfFile.value || totalPages.value === 0) {
    sidebarMessage.value = '請先載入 PDF'
    return
  }
  sidebarExporting.value = 'ppt'
  sidebarMessage.value = ''
  try {
    const blob = await exportPptFull(pdfFile.value, fullExportReplacements.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'output.pptx'
    a.click()
    URL.revokeObjectURL(url)
    sidebarMessage.value = 'PPT 已下載'
    toast.success('PPT 已下載')
  } catch (e) {
    sidebarMessage.value = '下載 PPT 失敗: ' + (e.message || String(e))
    toast.error('下載 PPT 失敗: ' + (e.message || String(e)))
  } finally {
    sidebarExporting.value = ''
  }
}

async function sidebarDownloadPngZip() {
  if (!pdfFile.value || totalPages.value === 0) {
    sidebarMessage.value = '請先載入 PDF'
    return
  }
  sidebarExporting.value = 'zip'
  sidebarMessage.value = ''
  try {
    const blob = await exportPngZipFull(pdfFile.value, fullExportReplacements.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'pages.zip'
    a.click()
    URL.revokeObjectURL(url)
    sidebarMessage.value = 'PNG 壓縮檔已下載'
    toast.success('PNG 壓縮檔已下載')
  } catch (e) {
    sidebarMessage.value = '下載壓縮檔失敗: ' + (e.message || String(e))
    toast.error('下載壓縮檔失敗: ' + (e.message || String(e)))
  } finally {
    sidebarExporting.value = ''
  }
}

// 頁面比例 485 × 271 公釐（橫向），避免預覽比例失調
const PAGE_ASPECT_RATIO = 485 / 271
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <header class="bg-slate-800 text-white px-6 py-5 shadow-lg">
      <h1 class="text-2xl font-bold tracking-tight">PDF 抹除儀表板</h1>
      <p class="text-slate-300 text-sm mt-1.5">載入 PDF → 選擇頁面 → 塗抹遮罩 → AI 抹除 → 輸出 PDF / PPT / 剪貼簿</p>
    </header>

    <div class="flex flex-1 gap-5 p-5">
      <!-- 左側控制區 -->
      <aside class="w-72 flex-shrink-0 space-y-4">
        <div class="bg-white rounded-xl shadow-sm border border-slate-200/80 p-4">
          <label class="block text-sm font-semibold text-slate-800 mb-2">PDF 檔案</label>
          <div
            role="button"
            tabindex="0"
            class="flex flex-col items-center justify-center w-full h-24 rounded-lg border-2 border-dashed transition-colors cursor-pointer select-none"
            :class="isDragging ? 'border-emerald-500 bg-emerald-50/80' : 'border-slate-300 bg-slate-50/80 hover:bg-slate-100/80'"
            @click="fileInputRef?.click()"
            @dragover.prevent="onDragOver"
            @dragleave="onDragLeave"
            @drop.prevent="onFileDrop"
          >
            <span class="text-sm text-slate-500">點擊或拖放 PDF</span>
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,application/pdf"
              class="hidden"
              @change="onFileSelect"
            />
          </div>
          <p v-if="pdfFile" class="mt-2 text-xs font-medium text-slate-600 truncate px-1">{{ pdfFile.name }}</p>
        </div>

        <div v-if="totalPages > 0" class="bg-white rounded-xl shadow-sm border border-slate-200/80 p-4">
          <PdfPageThumbnails
            :file="pdfFile"
            :current-page="currentPage"
            @select-page="(n) => (currentPage = n)"
          />
          <div class="mt-3 pt-3 border-t border-slate-200 space-y-2">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">匯出</p>
            <button
              type="button"
              class="w-full px-4 py-2.5 rounded-lg bg-slate-700 text-white hover:bg-slate-600 active:scale-[0.98] transition-all disabled:opacity-50 disabled:active:scale-100 text-sm font-medium"
              :disabled="!!sidebarExporting || !pdfFile || totalPages === 0"
              @click="sidebarDownloadPdf"
            >
              {{ sidebarExporting === 'pdf' ? '匯出中…' : '下載 PDF' }}
            </button>
            <button
              type="button"
              class="w-full px-4 py-2.5 rounded-lg bg-slate-700 text-white hover:bg-slate-600 active:scale-[0.98] transition-all disabled:opacity-50 disabled:active:scale-100 text-sm font-medium"
              :disabled="!!sidebarExporting || !pdfFile || totalPages === 0"
              @click="sidebarDownloadPpt"
            >
              {{ sidebarExporting === 'ppt' ? '匯出中…' : '下載 PPT' }}
            </button>
            <button
              type="button"
              class="w-full px-4 py-2.5 rounded-lg border-2 border-slate-300 bg-white hover:bg-slate-50 hover:border-slate-400 active:scale-[0.98] transition-all text-slate-700 disabled:opacity-50 disabled:active:scale-100 text-sm font-medium"
              :disabled="!!sidebarExporting || !pdfFile || totalPages === 0"
              @click="sidebarDownloadPngZip"
            >
              {{ sidebarExporting === 'zip' ? '壓縮中…' : '下載 PNG (壓縮檔)' }}
            </button>
          </div>
          <p v-if="sidebarMessage" class="mt-2 text-xs text-slate-500">{{ sidebarMessage }}</p>
        </div>

      </aside>

      <!-- 主內容：預覽 + 遮罩疊加 -->
      <main class="flex-1 min-w-0">
        <div class="bg-white rounded-xl shadow-sm border border-slate-200/80 overflow-hidden">
          <!-- 工具列：筆刷 + 動作 -->
          <div class="flex flex-wrap items-center gap-4 px-4 py-3 bg-slate-50/90 border-b border-slate-200">
            <div class="flex items-center gap-3">
              <span class="text-sm font-medium text-slate-600">筆刷</span>
              <input
                v-model.number="brushSize"
                type="range"
                min="8"
                max="80"
                class="h-2 w-28 accent-slate-600 rounded-full appearance-none bg-slate-200 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-slate-600 [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-sm"
              />
              <span class="text-sm tabular-nums font-medium text-slate-700 min-w-[2.25rem]">{{ brushSize }}px</span>
            </div>
            <div class="h-5 w-px bg-slate-300 hidden sm:block" aria-hidden="true" />
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 active:scale-[0.98] transition-all font-medium text-sm shadow-sm disabled:opacity-50 disabled:pointer-events-none"
                :disabled="!pdfFile || inpaintLoading"
                @click="runInpaint"
              >
                {{ inpaintLoading ? '運算中…' : '執行 AI 抹除' }}
              </button>
              <button
                type="button"
                class="px-4 py-2 rounded-lg border-2 border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-400 active:scale-[0.98] transition-all font-medium text-sm"
                :disabled="!canvasSize.width"
                @click="clearMask"
              >
                清除遮罩
              </button>
            </div>
          </div>
          <!-- 標題列 + 縮放 -->
          <div class="flex items-center justify-between px-4 py-2.5">
            <h2 class="text-sm font-semibold text-slate-700">預覽與遮罩（紅色區域為要抹除處）</h2>
            <div class="flex items-center gap-1 rounded-lg bg-slate-100/80 p-1">
              <button
                type="button"
                class="w-8 h-8 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-600 font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="縮小"
                :disabled="previewZoom <= PREVIEW_ZOOM_MIN"
                @click="zoomOut"
              >
                −
              </button>
              <button
                type="button"
                class="min-w-[3.5rem] h-8 px-2 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors"
                :title="`目前 ${Math.round(previewZoom * 100)}%`"
                @click="zoomReset"
              >
                {{ Math.round(previewZoom * 100) }}%
              </button>
              <button
                type="button"
                class="w-8 h-8 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-600 font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="放大"
                :disabled="previewZoom >= PREVIEW_ZOOM_MAX"
                @click="zoomIn"
              >
                +
              </button>
            </div>
          </div>
          <div class="px-4 pb-4">
          <div
            ref="previewContainerRef"
            class="relative w-full max-w-full max-h-[40vh] bg-slate-100 rounded-lg overflow-auto border border-slate-200"
            :style="pdfFile ? { aspectRatio: PAGE_ASPECT_RATIO } : { minHeight: '200px' }"
          >
            <div
              class="relative"
              :style="{
                width: previewViewportSize.width ? `${previewViewportSize.width * previewZoom}px` : '100%',
                height: previewViewportSize.height ? `${previewViewportSize.height * previewZoom}px` : '100%',
                minWidth: '100%',
                minHeight: '100%',
              }"
            >
              <div
                class="absolute left-0 top-0 origin-top-left"
                :style="{
                  width: previewViewportSize.width ? `${previewViewportSize.width}px` : '100%',
                  height: previewViewportSize.height ? `${previewViewportSize.height}px` : '100%',
                  transform: `scale(${previewZoom})`,
                }"
              >
                <div class="relative w-full h-full min-h-[200px] flex items-center justify-center bg-slate-100 rounded-lg overflow-hidden">
                  <PdfViewer
                    v-if="!appliedImageBlob"
                    ref="pdfViewerRef"
                    :file="pdfFile"
                    :page-num="currentPage"
                    :scale="scale"
                    @total-pages="onTotalPages"
                    @page-image="onPageImage"
                    @dimensions="onDimensions"
                  />
                  <img
                    v-else
                    :src="appliedImageUrl"
                    alt="已套用的頁面"
                    class="max-w-full max-h-full object-contain block"
                    :width="effectiveCanvasSize.width"
                    :height="effectiveCanvasSize.height"
                  />
                  <MaskCanvas
                    v-if="effectiveCanvasSize.width && effectiveCanvasSize.height"
                    ref="maskCanvasRef"
                    :width="effectiveCanvasSize.width"
                    :height="effectiveCanvasSize.height"
                    :brush-size="brushSize"
                  />
                </div>
              </div>
            </div>
          </div>
          </div>
          <p v-if="inpaintError" class="mt-2 mx-4 mb-2 text-sm text-red-600">{{ inpaintError }}</p>
        </div>

        <div v-if="resultImageBlob" class="mt-5 bg-white rounded-xl shadow-sm border border-slate-200/80 p-4">
          <h2 class="text-sm font-semibold text-slate-700 mb-3">抹除結果</h2>
          <img
            :src="resultImageUrl"
            alt="結果"
            class="max-w-full max-h-[40vh] w-full h-auto rounded-lg border border-slate-200 object-contain"
            :style="{ aspectRatio: PAGE_ASPECT_RATIO }"
          />
          <div class="mt-3 flex flex-wrap gap-3 items-center">
            <button
              type="button"
              class="px-4 py-2.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 active:scale-[0.98] transition-all font-medium shadow-sm"
              @click="applyResult"
            >
              套用
            </button>
            <span class="text-xs text-slate-500">套用後此圖會覆蓋預覽底圖，可繼續塗抹再抹除</span>
          </div>
          <div class="mt-3 pt-3 border-t border-slate-200">
            <ExportButtons
              :result-image-blob="resultImageBlob"
              :current-page-image-blob="effectivePageBlob"
              :pdf-file="pdfFile"
              :current-page-index="currentPageIndex"
              :all-page-blobs="allPageBlobs"
              :get-mask-blob="getMaskBlobForExport"
            />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
