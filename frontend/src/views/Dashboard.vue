<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount, onMounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.mjs?url'
import PdfViewer from '../components/PdfViewer.vue'
import PdfPageThumbnails from '../components/PdfPageThumbnails.vue'
import MaskCanvas from '../components/MaskCanvas.vue'
import ExportButtons from '../components/ExportButtons.vue'
import { usePdfInpaintStore } from '../stores/pdfInpaint'
import { useToast } from '../composables/useToast'
import { useOcr } from '../composables/useOcr'
import { inpaint } from '../api/inpaint'
import { exportPdfFull, exportPptFull, exportPngZipFull } from '../api/export'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

const store = usePdfInpaintStore()
const toast = useToast()

const pdfFile = ref(null)
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(2)
const brushSize = ref(24)
const canvasSize = ref({ width: 0, height: 0 })
const pageImageBlob = ref(null)
const resultImageUrl = ref('')
const appliedImageUrl = ref('')
const inpaintLoading = ref(false)
const inpaintError = ref('')
const pdfViewerRef = ref(null)
const maskCanvasRef = ref(null)
const fileInputRef = ref(null)
const isDragging = ref(false)
const maskMode = ref('brush')
const { loading: ocrLoading, recognizeFromBlob } = useOcr()
const allOcrLoading = ref(false)
const allOcrProgress = ref({ done: 0, total: 0 })
let allOcrRunToken = 0

const ocrItems = computed(() => store.getOcrItems(currentPage.value))
const ocrError = computed(() => store.getOcrError(currentPage.value))
const selectedOcrIds = computed(() => new Set(store.getSelectedOcrIds(currentPage.value)))

const resultImageBlob = computed(() => store.getResult(currentPage.value))
const appliedImageBlob = computed(() => store.getApplied(currentPage.value))

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

watch(pdfFile, () => {
  store.clearAll()
  pageImageBlob.value = null
  canvasSize.value = { width: 0, height: 0 }
  allOcrLoading.value = false
  allOcrProgress.value = { done: 0, total: 0 }
  allOcrRunToken += 1
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

const effectivePageBlob = computed(() => appliedImageBlob.value || pageImageBlob.value)

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
  store.clearMaskSnapshot(currentPage.value)
  store.setSelectedOcrIds(currentPage.value, [])
}

function applyResult() {
  const blob = resultImageBlob.value
  if (!blob) return
  store.setApplied(currentPage.value, blob)
  clearMask()
  toast.success('已套用')
}

function normalizeRect(rect) {
  const width = effectiveCanvasSize.value.width || 0
  const height = effectiveCanvasSize.value.height || 0
  if (!width || !height) return null
  const x = Math.max(0, Math.min(width, Number(rect?.x ?? 0)))
  const y = Math.max(0, Math.min(height, Number(rect?.y ?? 0)))
  const w = Math.max(1, Number(rect?.width ?? 0))
  const h = Math.max(1, Number(rect?.height ?? 0))
  return {
    x,
    y,
    width: Math.max(1, Math.min(width - x, w)),
    height: Math.max(1, Math.min(height - y, h)),
  }
}

function toggleOcrMask(item) {
  const rect = normalizeRect(item?.rect)
  if (!rect) return
  const next = new Set(selectedOcrIds.value)
  if (next.has(item.id)) {
    next.delete(item.id)
    store.setSelectedOcrIds(currentPage.value, Array.from(next))
    maskCanvasRef.value?.removeRectMask?.(rect)
  } else {
    maskCanvasRef.value?.applyRectMask?.(rect)
    next.add(item.id)
    store.setSelectedOcrIds(currentPage.value, Array.from(next))
  }
}

function rectsIntersect(a, b) {
  return !(
    a.x + a.width <= b.x ||
    b.x + b.width <= a.x ||
    a.y + a.height <= b.y ||
    b.y + b.height <= a.y
  )
}

function onMaskRectCommit(rect) {
  if (maskMode.value !== 'rectangleBatch') return
  const sel = normalizeRect(rect)
  if (!sel) return
  if (!ocrItems.value.length) {
    toast.error('請先按「辨識」產生 OCR 區塊')
    return
  }
  const next = new Set(selectedOcrIds.value)
  let count = 0
  for (const item of ocrItems.value) {
    const r = normalizeRect(item.rect)
    if (!r || !rectsIntersect(sel, r)) continue
    maskCanvasRef.value?.applyRectMask?.(r)
    next.add(item.id)
    count += 1
  }
  store.setSelectedOcrIds(currentPage.value, Array.from(next))
  if (count > 0) toast.success(`已為 ${count} 個 OCR 區塊加上遮罩`)
  else toast.error('框選範圍內沒有 OCR 區塊')
}

function clearOcrItems(pageNum = currentPage.value) {
  store.clearOcrState(pageNum)
}

async function runOcr() {
  const base = effectivePageBlob.value
  if (!base) {
    store.setOcrError(currentPage.value, '請先載入 PDF 並選擇頁面')
    return
  }
  store.setOcrError(currentPage.value, '')
  try {
    const items = await recognizeFromBlob(base)
    store.setOcrItems(currentPage.value, items)
    store.setSelectedOcrIds(currentPage.value, [])
    if (!items.length) {
      toast.error('此頁未辨識到可用文字區塊')
    } else {
      toast.success(`辨識完成，共 ${items.length} 個區塊`)
    }
  } catch (e) {
    const message = e?.message || String(e)
    store.setOcrError(currentPage.value, message)
    toast.error(message)
  }
}

async function renderPdfPageBlob(doc, pageNum) {
  const page = await doc.getPage(pageNum)
  const viewport = page.getViewport({ scale: 1 })
  const canvas = document.createElement('canvas')
  canvas.width = viewport.width
  canvas.height = viewport.height
  const ctx = canvas.getContext('2d')
  await page.render({
    canvasContext: ctx,
    viewport,
  }).promise

  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob((out) => {
      if (out) resolve(out)
      else reject(new Error(`第 ${pageNum} 頁轉成圖片失敗`))
    }, 'image/png', 1)
  })

  return {
    blob,
    width: viewport.width,
    height: viewport.height,
  }
}

async function getOcrSourceForPage(doc, pageNum) {
  if (pageNum === currentPage.value && effectivePageBlob.value) {
    return {
      blob: effectivePageBlob.value,
      width: effectiveCanvasSize.value.width,
      height: effectiveCanvasSize.value.height,
    }
  }

  const storedBlob = store.getApplied(pageNum) || store.getResult(pageNum)
  const storedSize = store.getDimensions(pageNum)
  if (storedBlob) {
    return {
      blob: storedBlob,
      width: storedSize?.width || 0,
      height: storedSize?.height || 0,
    }
  }

  return renderPdfPageBlob(doc, pageNum)
}

async function runOcrAllPages() {
  if (!pdfFile.value || totalPages.value === 0) {
    toast.error('請先載入 PDF')
    return
  }

  const runToken = ++allOcrRunToken
  allOcrLoading.value = true
  allOcrProgress.value = { done: 0, total: totalPages.value }

  try {
    const data = await pdfFile.value.arrayBuffer()
    const doc = await pdfjsLib.getDocument({ data }).promise

    for (let pageNum = 1; pageNum <= doc.numPages; pageNum += 1) {
      if (runToken !== allOcrRunToken) return

      store.setOcrError(pageNum, '')
      const { blob, width, height } = await getOcrSourceForPage(doc, pageNum)
      if (width && height) {
        store.setDimensions(pageNum, width, height)
      }

      try {
        const items = await recognizeFromBlob(blob)
        store.setOcrItems(pageNum, items)
        store.setSelectedOcrIds(pageNum, [])
      } catch (e) {
        store.setOcrItems(pageNum, [])
        store.setOcrError(pageNum, e?.message || String(e))
      }

      allOcrProgress.value = { done: pageNum, total: doc.numPages }
    }

    if (runToken !== allOcrRunToken) return
    toast.success(`全部頁面辨識完成，共 ${doc.numPages} 頁`)
  } catch (e) {
    toast.error(e?.message || String(e))
  } finally {
    if (runToken === allOcrRunToken) {
      allOcrLoading.value = false
      allOcrProgress.value = { done: 0, total: totalPages.value }
    }
  }
}

async function saveMaskSnapshot(pageNum) {
  if (!pageNum || !maskCanvasRef.value?.exportMaskSnapshot) return
  const snapshot = maskCanvasRef.value.exportMaskSnapshot()
  if (snapshot) store.setMaskSnapshot(pageNum, snapshot)
}

async function restoreMaskSnapshot(pageNum) {
  await nextTick()
  const canvas = maskCanvasRef.value
  if (!canvas) return
  const snapshot = store.getMaskSnapshot(pageNum)
  if (snapshot) await canvas.importMaskSnapshot?.(snapshot)
  else canvas.clearMask?.()
}

watch(currentPage, async (nextPage, prevPage) => {
  if (prevPage && prevPage !== nextPage) {
    await saveMaskSnapshot(prevPage)
  }
  await restoreMaskSnapshot(nextPage)
})

watch(
  () => [effectiveCanvasSize.value.width, effectiveCanvasSize.value.height],
  async () => {
    if (!effectiveCanvasSize.value.width || !effectiveCanvasSize.value.height) return
    await restoreMaskSnapshot(currentPage.value)
  }
)

const allPageBlobs = computed(() =>
  resultImageBlob.value ? [resultImageBlob.value] : []
)

function getMaskBlobForExport() {
  return maskCanvasRef.value?.getMaskBlob?.() ?? Promise.resolve(null)
}

const fullExportReplacements = computed(() => {
  const out = {}
  for (const pageNum of store.pageNumbersWithContent) {
    const blob = store.getApplied(pageNum) || store.getResult(pageNum)
    if (blob) out[pageNum - 1] = blob
  }
  return out
})

const sidebarExporting = ref('')
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

const PAGE_ASPECT_RATIO = 485 / 271
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <header class="bg-slate-800 text-white px-6 py-5 shadow-lg">
      <h1 class="text-2xl font-bold tracking-tight">PDF 抹除儀表板</h1>
      <p class="text-slate-300 text-sm mt-1.5">載入 PDF → 選擇頁面 → OCR 辨識區塊上遮罩 / 手動畫遮罩 → AI 抹除 → 輸出 PDF / PPT / 剪貼簿</p>
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
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-slate-600">工具</span>
              <div class="flex rounded-lg border border-slate-300 bg-white p-0.5" role="tablist">
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                  :class="maskMode === 'brush' ? 'bg-slate-200 text-slate-800 shadow-sm' : 'text-slate-600 hover:bg-slate-100'"
                  @click="maskMode = 'brush'"
                >
                  筆刷
                </button>
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                  :class="maskMode === 'rectangle' ? 'bg-slate-200 text-slate-800 shadow-sm' : 'text-slate-600 hover:bg-slate-100'"
                  @click="maskMode = 'rectangle'"
                >
                  框選
                </button>
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                  :class="maskMode === 'rectangleBatch' ? 'bg-slate-200 text-slate-800 shadow-sm' : 'text-slate-600 hover:bg-slate-100'"
                  title="拖曳框選後，將範圍內所有 OCR 區塊一次套上遮罩（需先辨識）"
                  @click="maskMode = 'rectangleBatch'"
                >
                  批次框選
                </button>
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                  :class="maskMode === 'eraser' ? 'bg-slate-200 text-slate-800 shadow-sm' : 'text-slate-600 hover:bg-slate-100'"
                  @click="maskMode = 'eraser'"
                >
                  橡皮擦
                </button>
              </div>
            </div>
            <p
              v-if="maskMode === 'rectangleBatch'"
              class="w-full text-xs text-sky-700 bg-sky-50 border border-sky-200 rounded-md px-2 py-1.5"
            >
              批次框選：在預覽上拖曳矩形，放開後會對範圍內的 OCR 區塊逐一上遮罩（請先按「辨識」）。
            </p>
            <div v-show="maskMode === 'brush' || maskMode === 'eraser'" class="flex items-center gap-3">
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
                class="px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-500 active:scale-[0.98] transition-all font-medium text-sm shadow-sm disabled:opacity-50 disabled:pointer-events-none"
                :disabled="!pdfFile || !effectivePageBlob || ocrLoading || allOcrLoading"
                @click="runOcr"
              >
                {{ ocrLoading ? '辨識中…' : '辨識' }}
              </button>
              <button
                type="button"
                class="px-4 py-2 rounded-lg bg-cyan-700 text-white hover:bg-cyan-600 active:scale-[0.98] transition-all font-medium text-sm shadow-sm disabled:opacity-50 disabled:pointer-events-none"
                :disabled="!pdfFile || totalPages === 0 || ocrLoading || allOcrLoading"
                @click="runOcrAllPages"
              >
                {{ allOcrLoading ? `全部辨識中 ${allOcrProgress.done}/${allOcrProgress.total}` : '全部辨識' }}
              </button>
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
                    :mode="maskMode"
                    @rect-commit="onMaskRectCommit"
                  />
                  <svg
                    v-if="ocrItems.length && effectiveCanvasSize.width && effectiveCanvasSize.height"
                    class="absolute inset-0 w-full h-full pointer-events-none"
                    :viewBox="`0 0 ${effectiveCanvasSize.width} ${effectiveCanvasSize.height}`"
                    preserveAspectRatio="xMidYMid meet"
                  >
                    <g v-for="item in ocrItems" :key="item.id" @click.stop="toggleOcrMask(item)">
                      <rect
                        :x="item.rect.x"
                        :y="item.rect.y"
                        :width="item.rect.width"
                        :height="item.rect.height"
                        :fill="selectedOcrIds.has(item.id) ? 'rgba(16, 185, 129, 0.25)' : 'rgba(59, 130, 246, 0.18)'"
                        :stroke="selectedOcrIds.has(item.id) ? 'rgba(5, 150, 105, 0.95)' : 'rgba(37, 99, 235, 0.95)'"
                        stroke-width="1.5"
                        class="cursor-pointer pointer-events-auto"
                      />
                    </g>
                  </svg>
                </div>
              </div>
            </div>
          </div>
          </div>
          <p v-if="inpaintError" class="mt-2 mx-4 mb-2 text-sm text-red-600">{{ inpaintError }}</p>
          <p v-if="allOcrLoading" class="mt-2 mx-4 text-xs text-cyan-700">
            正在逐頁辨識，切換頁面不會中斷；目前進度 {{ allOcrProgress.done }} / {{ allOcrProgress.total }}。
          </p>
          <div v-if="ocrItems.length || ocrError" class="mx-4 mb-3 text-xs text-slate-600">
            <p v-if="ocrError" class="text-red-600 mb-1">{{ ocrError }}</p>
            <div v-if="ocrItems.length" class="flex items-center justify-between">
              <span>已辨識 {{ ocrItems.length }} 個文字區塊；點一下上遮罩，再點一次可移除。也可用「批次框選」一次套用多個區塊。</span>
              <button type="button" class="text-slate-500 hover:text-slate-800 underline" @click="clearOcrItems">
                清空辨識框
              </button>
            </div>
          </div>
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
