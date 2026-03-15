<script setup>
import { ref } from 'vue'
import { exportPdf, exportPdfFromPdf, exportPpt } from '../api/export'

const props = defineProps({
  resultImageBlob: { type: Blob, default: null },
  currentPageImageBlob: { type: Blob, default: null },
  pdfFile: { type: File, default: null },
  currentPageIndex: { type: Number, default: 0 },
  allPageBlobs: { type: Array, default: () => [] },
  /** 取得當前遮罩 Blob（用於 PDF 匯出） */
  getMaskBlob: { type: Function, default: null },
})

const copying = ref(false)
const exportingPdf = ref(false)
const exportingPpt = ref(false)
const message = ref('')

async function copyToClipboard() {
  const blob = props.resultImageBlob
  if (!blob) {
    message.value = '請先執行 AI 抹除'
    return
  }
  copying.value = true
  message.value = ''
  try {
    const item = new ClipboardItem({ 'image/png': blob })
    await navigator.clipboard.write([item])
    message.value = '已複製到剪貼簿'
  } catch (e) {
    message.value = '複製失敗: ' + (e.message || String(e))
  } finally {
    copying.value = false
  }
}

async function downloadPdf() {
  const maskBlob = props.getMaskBlob ? await props.getMaskBlob() : null
  if (props.pdfFile && maskBlob != null && props.resultImageBlob) {
    exportingPdf.value = true
    message.value = ''
    try {
      const blob = await exportPdfFromPdf(props.pdfFile, props.currentPageIndex, maskBlob)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'output.pdf'
      a.click()
      URL.revokeObjectURL(url)
      message.value = 'PDF 已下載'
    } catch (e) {
      message.value = '匯出 PDF 失敗: ' + (e.message || String(e))
    } finally {
      exportingPdf.value = false
    }
    return
  }
  if (props.allPageBlobs.length > 0) {
    exportingPdf.value = true
    message.value = ''
    try {
      const blob = await exportPdf(props.allPageBlobs)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'output.pdf'
      a.click()
      URL.revokeObjectURL(url)
      message.value = 'PDF 已下載'
    } catch (e) {
      message.value = '匯出 PDF 失敗: ' + (e.message || String(e))
    } finally {
      exportingPdf.value = false
    }
    return
  }
  message.value = '請先執行抹除或準備多頁圖片'
}

async function downloadPpt() {
  const blobs = props.allPageBlobs.length ? props.allPageBlobs : (props.resultImageBlob ? [props.resultImageBlob] : [])
  if (blobs.length === 0) {
    message.value = '請先執行抹除或準備多頁圖片'
    return
  }
  exportingPpt.value = true
  message.value = ''
  try {
    const blob = await exportPpt(blobs)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'output.pptx'
    a.click()
    URL.revokeObjectURL(url)
    message.value = 'PPT 已下載'
  } catch (e) {
    message.value = '匯出 PPT 失敗: ' + (e.message || String(e))
  } finally {
    exportingPpt.value = false
  }
}
</script>

<template>
  <div class="flex flex-wrap gap-3 items-center">
    <button
      type="button"
      class="px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50"
      :disabled="!resultImageBlob || copying"
      @click="copyToClipboard"
    >
      {{ copying ? '複製中…' : '複製到剪貼簿' }}
    </button>
    <button
      type="button"
      class="px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50"
      :disabled="exportingPdf"
      @click="downloadPdf"
    >
      {{ exportingPdf ? '匯出中…' : '下載 PDF' }}
    </button>
    <button
      type="button"
      class="px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50"
      :disabled="exportingPpt"
      @click="downloadPpt"
    >
      {{ exportingPpt ? '匯出中…' : '下載 PPT' }}
    </button>
    <span v-if="message" class="text-sm text-slate-600">{{ message }}</span>
  </div>
</template>
