<script setup>
import { ref, shallowRef, watch, nextTick, onMounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

const props = defineProps({
  file: { type: File, default: null },
  pageNum: { type: Number, default: 1 },
  /** 基礎縮放（會乘上 devicePixelRatio 以在高 DPI 螢幕輸出清晰圖，上限 4 避免過大 canvas） */
  scale: { type: Number, default: 2 },
})

const emit = defineEmits(['update:pageNum', 'totalPages', 'pageImage', 'dimensions'])

const canvasRef = ref(null)
// 使用 shallowRef：pdfjs 的 PDF 文件物件含 private fields，被 ref() 包成 Proxy 會導致 getPage 報錯
const pdfDoc = shallowRef(null)
const totalPages = ref(0)
const loading = ref(false)

async function loadPdf(file) {
  if (!file) {
    pdfDoc.value = null
    totalPages.value = 0
    return
  }
  loading.value = true
  try {
    const data = await file.arrayBuffer()
    const doc = await pdfjsLib.getDocument({ data }).promise
    pdfDoc.value = doc
    totalPages.value = doc.numPages
    emit('totalPages', doc.numPages)
  } catch (e) {
    console.error(e)
    pdfDoc.value = null
    totalPages.value = 0
  } finally {
    loading.value = false
  }
}

async function renderPage() {
  const doc = pdfDoc.value
  const canvas = canvasRef.value
  if (!doc || !canvas || props.pageNum < 1 || props.pageNum > totalPages.value) return
  const page = await doc.getPage(props.pageNum)
  // 高 DPI 螢幕用較高解析度渲染，匯出與顯示較清晰；上限 4 避免 canvas 過大
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
  const effectiveScale = Math.min(props.scale * dpr, 4)
  const viewport = page.getViewport({ scale: effectiveScale })
  canvas.width = viewport.width
  canvas.height = viewport.height
  const ctx = canvas.getContext('2d')
  await page.render({
    canvasContext: ctx,
    viewport,
  }).promise
  emit('dimensions', viewport.width, viewport.height)
  if (canvas.width && canvas.height) {
    canvas.toBlob(
      (blob) => emit('pageImage', blob),
      'image/png',
      1
    )
  }
}

watch(
  () => [props.file, props.pageNum, props.scale],
  async () => {
    try {
      if (props.file && !pdfDoc.value) await loadPdf(props.file)
      if (pdfDoc.value) {
        await nextTick() // 等 canvas 掛上 DOM 後再繪製
        await renderPage()
      }
    } catch (e) {
      console.error('PdfViewer render:', e)
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (props.file) loadPdf(props.file)
})

defineExpose({
  totalPages,
  renderPage,
  getCanvas: () => canvasRef.value,
})
</script>

<template>
  <div class="relative w-full h-full min-h-[200px] flex items-center justify-center bg-slate-100 rounded-lg overflow-hidden">
    <template v-if="loading">載入中…</template>
    <template v-else-if="!file">請選擇 PDF 檔案</template>
    <template v-else-if="pdfDoc">
      <canvas ref="canvasRef" class="max-w-full max-h-full object-contain block" />
    </template>
  </div>
</template>
