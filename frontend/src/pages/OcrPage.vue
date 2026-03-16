<script setup>
import { ref, onBeforeUnmount, watch, nextTick } from 'vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Alert from '../components/ui/Alert.vue'

const file = ref(null)
const previewUrl = ref('')
const loading = ref(false)
const error = ref('')
const results = ref([])
const canvasRef = ref(null)
// 最小信心分數（0~1），提高可以減少圖標/雜訊文字
const minScore = ref(0.9)

function revokePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

onBeforeUnmount(revokePreview)

function onFileChange(event) {
  revokePreview()
  results.value = []
  error.value = ''
  const f = event.target.files && event.target.files[0]
  if (!f) return
  if (!f.type.startsWith('image/')) {
    error.value = '請選擇圖片檔案'
    return
  }
  previewUrl.value = URL.createObjectURL(f)
}

/**
 * Expand bbox so drawn box fully covers text (PaddleOCR bbox can be tight, especially for large font).
 * Returns axis-aligned [x1, y1, x2, y2] with padding, clamped to image bounds.
 */
function expandBbox(pts, imgW, imgH) {
  const xs = pts.map((p) => p[0])
  const ys = pts.map((p) => p[1])
  let x1 = Math.min(...xs)
  let y1 = Math.min(...ys)
  let x2 = Math.max(...xs)
  let y2 = Math.max(...ys)
  const boxW = x2 - x1
  const boxH = y2 - y1
  const pad = Math.max(4, Math.min(boxW, boxH) * 0.08)
  x1 = Math.max(0, x1 - pad)
  y1 = Math.max(0, y1 - pad)
  x2 = Math.min(imgW, x2 + pad)
  y2 = Math.min(imgH, y2 + pad)
  return [x1, y1, x2, y2]
}

function drawBoxesOnImage() {
  if (!previewUrl.value || !results.value.length || !canvasRef.value) return
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    const canvas = canvasRef.value
    if (!canvas) return
    const w = img.naturalWidth
    const h = img.naturalHeight
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, 0, 0)
    const strokeColor = '#0d6efd'
    const lineWidth = Math.max(2, Math.min(w, h) / 400)
    ctx.strokeStyle = strokeColor
    ctx.lineWidth = lineWidth
    ctx.font = `${Math.max(12, lineWidth * 8)}px sans-serif`
    ctx.fillStyle = strokeColor
    ctx.textBaseline = 'top'
    results.value.forEach((item) => {
      const bbox = item.bbox
      if (!bbox || !Array.isArray(bbox) || bbox.length < 4) return
      const pts = bbox.map((p) => (Array.isArray(p) ? [Number(p[0]), Number(p[1])] : [0, 0]))
      const [x1, y1, x2, y2] = expandBbox(pts, w, h)
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
      const text = item.text != null ? String(item.text) : ''
      const confStr =
        item.confidence != null ? ` (${(item.confidence * 100).toFixed(1)}%)` : ''
      const labelText = text + confStr
      if (labelText) {
        const labelH = 18
        const labelY = Math.max(0, y1 - labelH - 2)
        const labelW = ctx.measureText(labelText).width + 4
        ctx.fillStyle = 'rgba(13, 110, 253, 0.9)'
        ctx.fillRect(x1, labelY, labelW, labelH)
        ctx.fillStyle = '#fff'
        ctx.fillText(labelText, x1 + 2, labelY + 2)
      }
    })
  }
  img.onerror = () => {}
  img.src = previewUrl.value
}

watch(
  () => [results.value.length, previewUrl.value],
  () => {
    if (results.value.length > 0 && previewUrl.value) {
      nextTick(() => drawBoxesOnImage())
    }
  }
)

async function submit() {
  if (!file.value || !file.value.files || !file.value.files[0]) {
    error.value = '請選擇一張圖片'
    return
  }
  const f = file.value.files[0]
  if (!f.type.startsWith('image/')) {
    error.value = '請選擇圖片檔案'
    return
  }
  loading.value = true
  error.value = ''
  results.value = []
  try {
    const form = new FormData()
    form.append('image', f)
    const params = new URLSearchParams()
    params.set('min_score', String(minScore.value))
    const res = await fetch(`/api/ocr?${params.toString()}`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const t = await res.text()
      throw new Error(t || `HTTP ${res.status}`)
    }
    const data = await res.json()
    results.value = data.results || []
  } catch (e) {
    error.value = e.message || '辨識失敗'
  } finally {
    loading.value = false
  }
}

function copyAllText() {
  if (!results.value.length) return
  const text = results.value.map((r) => r.text).join('\n')
  navigator.clipboard.writeText(text).then(
    () => {
      error.value = ''
      alert('已複製到剪貼簿')
    },
    () => {
      error.value = '複製失敗'
    }
  )
}

function downloadJson() {
  if (!results.value.length) return
  const blob = new Blob([JSON.stringify({ results: results.value }, null, 2)], {
    type: 'application/json',
  })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'ocr-results.json'
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<template>
  <div class="max-w-2xl md:max-w-3xl lg:max-w-4xl xl:max-w-5xl mx-auto text-left">
    <h1 class="text-xl font-semibold text-gray-900 dark:text-[var(--dracula-foreground)] mb-2">
      圖片辨識 (OCR)
    </h1>
    <p class="text-gray-600 dark:text-[var(--dracula-comment)] mb-6">
      上傳圖片，取得圖中的文字辨識結果。
    </p>
    <Card class="mb-6">
      <div class="flex flex-col gap-3">
        <label
          class="flex flex-col gap-1 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]"
        >
          最小信心分數（越高越少雜訊）：
          <div class="flex items-center gap-3">
            <input
              v-model.number="minScore"
              type="range"
              min="0.3"
              max="0.95"
              step="0.05"
              :disabled="loading"
              class="w-full"
            />
            <span class="w-12 text-right tabular-nums">{{ minScore.toFixed(2) }}</span>
          </div>
        </label>
        <input
          ref="file"
          type="file"
          accept="image/*"
          :disabled="loading"
          class="block w-full text-sm text-gray-900 dark:text-[var(--dracula-foreground)] file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary file:text-white file:cursor-pointer file:disabled:opacity-60"
          @change="onFileChange"
        />
        <div
          v-if="previewUrl && results.length === 0"
          class="max-w-full max-h-[200px] rounded-lg overflow-hidden border border-gray-200 dark:border-[var(--dracula-comment)]/50"
        >
          <img :src="previewUrl" alt="預覽" class="block max-w-full max-h-[200px] object-contain" />
        </div>
        <div
          v-if="results.length > 0 && previewUrl"
          class="rounded-lg overflow-hidden border border-gray-200 dark:border-[var(--dracula-comment)]/50 bg-gray-100 dark:bg-[var(--dracula-surface)]/80"
        >
          <canvas ref="canvasRef" class="block max-w-full max-h-[70vh] w-auto h-auto"></canvas>
          <p
            class="m-0 py-2 px-3 text-sm text-gray-600 dark:text-[var(--dracula-comment)] border-t border-gray-200 dark:border-[var(--dracula-comment)]/40"
          >
            辨識位置（藍框與文字標籤）
          </p>
        </div>
        <Button variant="primary" :loading="loading" @click="submit">
          {{ loading ? '辨識中…' : '上傳並辨識' }}
        </Button>
      </div>
    </Card>
    <Alert v-if="error" variant="error">{{ error }}</Alert>
    <Card v-if="results.length > 0" title="辨識結果" class="mb-6">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
        <span class="font-semibold text-sm text-gray-900 dark:text-[var(--dracula-foreground)]">
          辨識結果（{{ results.length }} 筆）
        </span>
        <div class="flex gap-2">
          <Button variant="secondary" @click="copyAllText">複製全部文字</Button>
          <Button variant="secondary" @click="downloadJson">下載 JSON</Button>
        </div>
      </div>
      <ol class="m-0 pl-5 max-h-64 overflow-y-auto space-y-1 list-decimal">
        <li
          v-for="(item, i) in results"
          :key="i"
          class="text-gray-800 dark:text-[var(--dracula-foreground)] break-words"
        >
          {{ item.text }}
          <span
            v-if="item.confidence != null"
            class="text-gray-500 dark:text-[var(--dracula-comment)] text-sm ml-1"
          >
            ({{ (item.confidence * 100).toFixed(1) }}%)
          </span>
        </li>
      </ol>
    </Card>
    <p
      v-else-if="!loading && !error && file?.files?.[0]"
      class="mt-4 text-gray-600 dark:text-[var(--dracula-comment)] text-sm"
    >
      尚無辨識結果，請點「上傳並辨識」。
    </p>
  </div>
</template>
