<script setup>
import { onBeforeUnmount, ref } from 'vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Select from '../components/ui/Select.vue'
import Alert from '../components/ui/Alert.vue'

const fileInput = ref(null)
const previewCanvas = ref(null)
const maskCanvas = ref(null)

const selectedFile = ref(null)
const originalImageUrl = ref('')
const resultImageUrl = ref('')
const loading = ref(false)
const error = ref('')
const brushSize = ref(40)
const backend = ref('lama')

const isDrawing = ref(false)
const hasMask = ref(false)

let imageElement = null

function revokeObjectUrl(url) {
  if (url) {
    URL.revokeObjectURL(url)
  }
}

onBeforeUnmount(() => {
  revokeObjectUrl(originalImageUrl.value)
  revokeObjectUrl(resultImageUrl.value)
})

function resetCanvases() {
  const canvas = previewCanvas.value
  const mask = maskCanvas.value
  if (!canvas || !mask || !imageElement) return

  const ctx = canvas.getContext('2d')
  const maskCtx = mask.getContext('2d')

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(imageElement, 0, 0, canvas.width, canvas.height)

  maskCtx.fillStyle = 'black'
  maskCtx.fillRect(0, 0, mask.width, mask.height)

  hasMask.value = false
}

function setupCanvasForImage(img) {
  const canvas = previewCanvas.value
  const mask = maskCanvas.value
  if (!canvas || !mask) return

  canvas.width = img.width
  canvas.height = img.height
  mask.width = img.width
  mask.height = img.height

  const maxDisplay = 640
  let displayW = img.width
  let displayH = img.height
  if (Math.max(displayW, displayH) > maxDisplay) {
    const scale = maxDisplay / Math.max(displayW, displayH)
    displayW = Math.round(displayW * scale)
    displayH = Math.round(displayH * scale)
  }
  canvas.style.width = `${displayW}px`
  canvas.style.height = `${displayH}px`
  mask.style.width = `${displayW}px`
  mask.style.height = `${displayH}px`

  resetCanvases()
}

function onFileChange(event) {
  const file = event.target.files && event.target.files[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    error.value = '請選擇圖片檔案'
    return
  }

  selectedFile.value = file
  error.value = ''

  if (originalImageUrl.value) {
    revokeObjectUrl(originalImageUrl.value)
    originalImageUrl.value = ''
  }
  if (resultImageUrl.value) {
    revokeObjectUrl(resultImageUrl.value)
    resultImageUrl.value = ''
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    const img = new Image()
    img.onload = () => {
      imageElement = img
      setupCanvasForImage(img)
      originalImageUrl.value = e.target.result
    }
    img.src = e.target.result
  }
  reader.readAsDataURL(file)
}

function getCanvasPoint(evt, canvas) {
  const rect = canvas.getBoundingClientRect()
  const x = evt.clientX - rect.left
  const y = evt.clientY - rect.top
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  return {
    x: x * scaleX,
    y: y * scaleY,
    radius: (brushSize.value / 2) * scaleX,
  }
}

function drawAtPointer(evt) {
  const canvas = previewCanvas.value
  const mask = maskCanvas.value
  if (!canvas || !mask || !imageElement) return

  const { x, y, radius } = getCanvasPoint(evt, canvas)

  const ctx = canvas.getContext('2d')
  const maskCtx = mask.getContext('2d')

  ctx.save()
  ctx.fillStyle = 'rgba(255, 0, 0, 0.4)'
  ctx.beginPath()
  ctx.arc(x, y, radius, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()

  maskCtx.save()
  maskCtx.fillStyle = '#ffffff'
  maskCtx.beginPath()
  maskCtx.arc(x, y, radius, 0, Math.PI * 2)
  maskCtx.fill()
  maskCtx.restore()

  hasMask.value = true
}

function handlePointerDown(evt) {
  if (!imageElement) {
    error.value = '請先選擇一張圖片'
    return
  }
  isDrawing.value = true
  drawAtPointer(evt)
}

function handlePointerMove(evt) {
  if (!isDrawing.value) return
  drawAtPointer(evt)
}

function stopDrawing() {
  isDrawing.value = false
}

function clearMask() {
  if (!imageElement) return
  resetCanvases()
}

async function submitInpaint() {
  if (!selectedFile.value) {
    error.value = '請先選擇一張圖片'
    return
  }
  const mask = maskCanvas.value
  if (!mask) {
    error.value = '遮罩畫布尚未就緒'
    return
  }

  loading.value = true
  error.value = ''

  if (resultImageUrl.value) {
    revokeObjectUrl(resultImageUrl.value)
    resultImageUrl.value = ''
  }

  try {
    const maskBlob = await new Promise((resolve, reject) => {
      mask.toBlob(
        (blob) => {
          if (blob) resolve(blob)
          else reject(new Error('產生遮罩失敗'))
        },
        'image/png',
        1
      )
    })

    const form = new FormData()
    form.append('image', selectedFile.value)
    form.append('mask', new File([maskBlob], 'mask.png', { type: 'image/png' }))

    const backendParam = encodeURIComponent(backend.value || 'sd')

    const res = await fetch(`/api/inpaint?backend=${backendParam}`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const t = await res.text()
      throw new Error(t || `HTTP ${res.status}`)
    }
    const blob = await res.blob()
    resultImageUrl.value = URL.createObjectURL(blob)
  } catch (e) {
    error.value = e.message || '智能抹除失敗'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto text-left pb-8">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-[var(--dracula-foreground)] mb-1">
      圖片智能抹除
    </h2>
    <p class="text-gray-600 dark:text-[var(--dracula-comment)] mb-6">
      上傳一張圖片，使用圓形畫筆在圖片上塗掉不要的內容，系統會自動補上自然背景。
    </p>

    <Card title="1. 選擇圖片" class="mb-6">
      <div class="space-y-4">
        <label class="flex flex-wrap items-center gap-2 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]">
          後端模型：
          <Select v-model="backend">
            <option value="sd">Stable Diffusion（較細緻，可能長出亂碼字）</option>
            <option value="lama">LaMa（較像傳統抹除，較少文字）</option>
          </Select>
        </label>
        <div>
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            :disabled="loading"
            class="block w-full text-sm text-gray-900 dark:text-[var(--dracula-foreground)] file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary file:text-white file:cursor-pointer file:disabled:opacity-60"
            @change="onFileChange"
          />
        </div>
      </div>
    </Card>

    <template v-if="selectedFile">
      <Card title="2. 使用畫筆塗掉不要的區域" class="mb-6">
        <div class="flex flex-wrap gap-4 items-center mb-3">
          <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]">
            畫筆大小：
            <input
              v-model.number="brushSize"
              type="range"
              min="10"
              max="80"
              class="w-40 accent-primary"
            />
            <span class="min-w-[3rem] text-right tabular-nums">{{ brushSize }} px</span>
          </label>
          <Button variant="secondary" :disabled="loading" @click="clearMask">
            清除遮罩
          </Button>
        </div>
        <div
          class="rounded-xl border border-gray-200 dark:border-[var(--dracula-comment)]/50 bg-gray-50 dark:bg-[var(--dracula-surface)]/80 p-3 overflow-auto"
        >
          <canvas
            ref="previewCanvas"
            class="block max-w-full touch-none cursor-crosshair"
            @pointerdown="handlePointerDown"
            @pointermove="handlePointerMove"
            @pointerup="stopDrawing"
            @pointerleave="stopDrawing"
          />
          <canvas ref="maskCanvas" class="hidden" aria-hidden="true" />
        </div>
        <p class="mt-2 text-sm text-gray-500 dark:text-[var(--dracula-comment)]">
          提示：紅色區域代表會被抹除的範圍。你可以多次塗抹或清除重畫。
        </p>
      </Card>

      <Card title="3. 開始智能抹除" class="mb-6">
        <Button variant="primary" :loading="loading" @click="submitInpaint">
          {{ loading ? '抹除中…' : '送出並抹除' }}
        </Button>
      </Card>
    </template>

    <Alert v-if="error" variant="error">{{ error }}</Alert>

    <Card v-if="resultImageUrl" title="4. 結果" class="mb-6">
      <div class="mb-3">
        <img
          :src="resultImageUrl"
          alt="Inpaint result"
          class="block max-w-full rounded-lg shadow-lg"
        />
      </div>
      <Button
        variant="secondary"
        @click="
          () => {
            const a = document.createElement('a')
            a.href = resultImageUrl
            a.download = 'inpainted.png'
            a.click()
          }
        "
      >
        下載結果圖片
      </Button>
    </Card>
  </div>
</template>
