<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount, onMounted } from 'vue'
import PdfViewer from '../components/PdfViewer.vue'
import PdfPageThumbnails from '../components/PdfPageThumbnails.vue'
import MaskCanvas from '../components/MaskCanvas.vue'
import ExportButtons from '../components/ExportButtons.vue'
import { usePdfInpaintStore } from '../stores/pdfInpaint'
import { inpaint } from '../api/inpaint'
import { exportPdfFull, exportPptFull, exportPngZipFull } from '../api/export'

const store = usePdfInpaintStore()

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

// 更換 PDF 時清空 store，避免與新檔混淆
watch(pdfFile, () => {
  store.clearAll()
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
    if (import.meta.env.DEV) {
      const apiMs = Math.round(performance.now() - t1)
      const totalMs = Math.round(performance.now() - t0)
      console.log(`[inpaint] API 請求: ${apiMs} ms | 按鈕到完成總計: ${totalMs} ms`)
    }
  } catch (e) {
    inpaintError.value = e.message || String(e)
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
}

// 供 ExportButtons：目前頁面有結果則用該 blob，多頁時可改為依 store.pageNumbersWithContent 彙總
const allPageBlobs = computed(() =>
  resultImageBlob.value ? [resultImageBlob.value] : []
)

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
  } catch (e) {
    sidebarMessage.value = '下載 PDF 失敗: ' + (e.message || String(e))
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
  } catch (e) {
    sidebarMessage.value = '下載 PPT 失敗: ' + (e.message || String(e))
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
  } catch (e) {
    sidebarMessage.value = '下載壓縮檔失敗: ' + (e.message || String(e))
  } finally {
    sidebarExporting.value = ''
  }
}

// 頁面比例 485 × 271 公釐（橫向），避免預覽比例失調
const PAGE_ASPECT_RATIO = 485 / 271
</script>

<template>
  <div class="min-h-screen bg-slate-200">
    <header class="bg-slate-800 text-white px-6 py-4 shadow">
      <h1 class="text-xl font-semibold">PDF 抹除儀表板</h1>
      <p class="text-slate-300 text-sm mt-1">載入 PDF → 選擇頁面 → 塗抹遮罩 → AI 抹除 → 輸出 PDF / PPT / 剪貼簿</p>
    </header>

    <div class="flex flex-1 gap-4 p-4">
      <!-- 左側控制區 -->
      <aside class="w-72 flex-shrink-0 space-y-4">
        <div class="bg-white rounded-lg shadow p-4">
          <label class="block text-sm font-medium text-slate-700 mb-2">PDF 檔案</label>
          <input
            type="file"
            accept=".pdf,application/pdf"
            class="block w-full text-sm text-slate-600 file:mr-3 file:py-2 file:px-4 file:rounded file:border-0 file:bg-slate-100 file:text-slate-700"
            @change="(e) => { pdfFile = e.target.files?.[0] || null; currentPage = 1 }"
          />
          <p v-if="pdfFile" class="mt-2 text-xs text-slate-500 truncate">{{ pdfFile.name }}</p>
        </div>

        <div v-if="totalPages > 0" class="bg-white rounded-lg shadow p-4">
          <PdfPageThumbnails
            :file="pdfFile"
            :current-page="currentPage"
            @select-page="(n) => (currentPage = n)"
          />
          <div class="mt-3 pt-3 border-t border-slate-200 space-y-2">
            <button
              type="button"
              class="w-full px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50 text-sm"
              :disabled="!!sidebarExporting || !pdfFile || totalPages === 0"
              @click="sidebarDownloadPdf"
            >
              {{ sidebarExporting === 'pdf' ? '匯出中…' : '下載 PDF' }}
            </button>
            <button
              type="button"
              class="w-full px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50 text-sm"
              :disabled="!!sidebarExporting || !pdfFile || totalPages === 0"
              @click="sidebarDownloadPpt"
            >
              {{ sidebarExporting === 'ppt' ? '匯出中…' : '下載 PPT' }}
            </button>
            <button
              type="button"
              class="w-full px-4 py-2 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-50 text-sm"
              :disabled="!!sidebarExporting || !pdfFile || totalPages === 0"
              @click="sidebarDownloadPngZip"
            >
              {{ sidebarExporting === 'zip' ? '壓縮中…' : '下載 PNG (壓縮檔)' }}
            </button>
          </div>
          <p v-if="sidebarMessage" class="mt-2 text-xs text-slate-500">{{ sidebarMessage }}</p>
        </div>

        <div class="bg-white rounded-lg shadow p-4">
          <label class="block text-sm font-medium text-slate-700 mb-2">筆刷大小</label>
          <input
            v-model.number="brushSize"
            type="range"
            min="8"
            max="80"
            class="w-full"
          />
          <span class="text-xs text-slate-500">{{ brushSize }}px</span>
        </div>

        <div class="bg-white rounded-lg shadow p-4 space-y-2">
          <button
            type="button"
            class="w-full px-4 py-2 rounded-lg bg-slate-600 text-white hover:bg-slate-500 disabled:opacity-50"
            :disabled="!pdfFile || inpaintLoading"
            @click="runInpaint"
          >
            {{ inpaintLoading ? '運算中…' : '執行 AI 抹除' }}
          </button>
          <button
            type="button"
            class="w-full px-4 py-2 rounded border border-slate-300 hover:bg-slate-50"
            :disabled="!canvasSize.width"
            @click="clearMask"
          >
            清除遮罩
          </button>
        </div>
      </aside>

      <!-- 主內容：預覽 + 遮罩疊加 -->
      <main class="flex-1 min-w-0">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-sm font-medium text-slate-700">預覽與遮罩（紅色區域為要抹除處）</h2>
            <div class="flex items-center gap-1">
              <button
                type="button"
                class="w-8 h-8 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-600 font-medium disabled:opacity-50"
                title="縮小"
                :disabled="previewZoom <= PREVIEW_ZOOM_MIN"
                @click="zoomOut"
              >
                −
              </button>
              <button
                type="button"
                class="min-w-[4rem] h-8 px-2 rounded border border-slate-300 bg-slate-50 text-slate-700 text-sm"
                :title="`目前 ${Math.round(previewZoom * 100)}%`"
                @click="zoomReset"
              >
                {{ Math.round(previewZoom * 100) }}%
              </button>
              <button
                type="button"
                class="w-8 h-8 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-600 font-medium disabled:opacity-50"
                title="放大"
                :disabled="previewZoom >= PREVIEW_ZOOM_MAX"
                @click="zoomIn"
              >
                +
              </button>
            </div>
          </div>
          <div
            ref="previewContainerRef"
            class="relative w-full max-w-full max-h-[60vh] bg-slate-100 rounded-lg overflow-auto"
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
          <p v-if="inpaintError" class="mt-2 text-sm text-red-600">{{ inpaintError }}</p>
        </div>

        <div v-if="resultImageBlob" class="mt-4 bg-white rounded-lg shadow p-4">
          <h2 class="text-sm font-medium text-slate-700 mb-2">抹除結果</h2>
          <img
            :src="resultImageUrl"
            alt="結果"
            class="max-w-full w-full h-auto rounded border border-slate-200 object-contain"
            :style="{ aspectRatio: PAGE_ASPECT_RATIO }"
          />
          <div class="mt-3 flex flex-wrap gap-3 items-center">
            <button
              type="button"
              class="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50"
              @click="applyResult"
            >
              套用
            </button>
            <span class="text-xs text-slate-500">套用後此圖會覆蓋預覽底圖，可繼續塗抹再抹除</span>
          </div>
          <div class="mt-3">
            <ExportButtons
              :result-image-blob="resultImageBlob"
              :current-page-image-blob="effectivePageBlob"
              :pdf-file="pdfFile"
              :current-page-index="currentPageIndex"
              :all-page-blobs="allPageBlobs"
              :get-mask-blob="() => maskCanvasRef?.value?.getMaskBlob?.() ?? Promise.resolve(null)"
            />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
