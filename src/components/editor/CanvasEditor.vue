<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useEditorStore } from '../../stores/useEditorStore'

const props = defineProps<{
  clearTrigger: number
}>()

const editor = useEditorStore()

const containerRef = ref<HTMLDivElement | null>(null)
const imageCanvasRef = ref<HTMLCanvasElement | null>(null)
const maskCanvasRef = ref<HTMLCanvasElement | null>(null)

interface DrawInfo {
  imageWidth: number
  imageHeight: number
  offsetX: number
  offsetY: number
  drawWidth: number
  drawHeight: number
}

let lastDrawInfo: DrawInfo | null = null

let drawing = false
let lastX = 0
let lastY = 0
const brushSize = 18

function resizeCanvasesToContainer() {
  const container = containerRef.value
  const imageCanvas = imageCanvasRef.value
  const maskCanvas = maskCanvasRef.value
  if (!container || !imageCanvas || !maskCanvas) return

  const rect = container.getBoundingClientRect()
  const width = rect.width
  const height = rect.height

  imageCanvas.width = width
  imageCanvas.height = height
  maskCanvas.width = width
  maskCanvas.height = height

  drawImage()
}

function drawImage() {
  const imageCanvas = imageCanvasRef.value
  if (!imageCanvas || !editor.originalImageDataUrl) return
  const ctx = imageCanvas.getContext('2d')
  if (!ctx) return

  const img = new Image()
  img.onload = () => {
    ctx.clearRect(0, 0, imageCanvas.width, imageCanvas.height)
    const canvasRatio = imageCanvas.width / imageCanvas.height
    const imgRatio = img.width / img.height

    let drawWidth = imageCanvas.width
    let drawHeight = imageCanvas.height
    let offsetX = 0
    let offsetY = 0

    if (imgRatio > canvasRatio) {
      drawWidth = imageCanvas.width
      drawHeight = drawWidth / imgRatio
      offsetY = (imageCanvas.height - drawHeight) / 2
    } else {
      drawHeight = imageCanvas.height
      drawWidth = drawHeight * imgRatio
      offsetX = (imageCanvas.width - drawWidth) / 2
    }

    lastDrawInfo = {
      imageWidth: img.width,
      imageHeight: img.height,
      offsetX,
      offsetY,
      drawWidth,
      drawHeight,
    }

    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight)
  }
  img.src = editor.originalImageDataUrl
}

function clearMask() {
  const maskCanvas = maskCanvasRef.value
  if (!maskCanvas) return
  const ctx = maskCanvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height)
}

function getCanvasPoint(event: PointerEvent): { x: number; y: number } | null {
  const canvas = maskCanvasRef.value
  if (!canvas) return null
  const rect = canvas.getBoundingClientRect()
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  }
}

function onPointerDown(event: PointerEvent) {
  if (!maskCanvasRef.value) return
  const point = getCanvasPoint(event)
  if (!point) return
  drawing = true
  lastX = point.x
  lastY = point.y
  drawStroke(point.x, point.y, false)
}

function onPointerMove(event: PointerEvent) {
  if (!drawing) return
  const point = getCanvasPoint(event)
  if (!point) return
  drawStroke(point.x, point.y, true)
  lastX = point.x
  lastY = point.y
}

function onPointerUp() {
  drawing = false
}

function drawStroke(x: number, y: number, connect: boolean) {
  const canvas = maskCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.save()
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = 'rgba(255,255,255,1)'
  ctx.fillStyle = 'rgba(255,255,255,1)'
  ctx.lineWidth = brushSize

  if (connect) {
    ctx.beginPath()
    ctx.moveTo(lastX, lastY)
    ctx.lineTo(x, y)
    ctx.stroke()
  } else {
    ctx.beginPath()
    ctx.arc(x, y, brushSize / 2, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.restore()
}

function getMaskImageDataInternal(): ImageData | null {
  const canvas = maskCanvasRef.value
  if (!canvas) return null
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const baseMask = ctx.getImageData(0, 0, canvas.width, canvas.height)

  // 若尚未有圖片繪製資訊，退回原本行為
  if (!lastDrawInfo) {
    return baseMask
  }

  const { imageWidth, imageHeight, offsetX, offsetY, drawWidth, drawHeight } =
    lastDrawInfo

  // 我們的模型固定吃 512x512，這裡直接把遮罩重新對齊並轉成 512x512
  const MODEL_SIZE = 512
  const outCanvas = document.createElement('canvas')
  outCanvas.width = MODEL_SIZE
  outCanvas.height = MODEL_SIZE
  const outCtx = outCanvas.getContext('2d')
  if (!outCtx) return baseMask

  const outImageData = outCtx.createImageData(MODEL_SIZE, MODEL_SIZE)
  const outData = outImageData.data
  const srcData = baseMask.data

  const sx = drawWidth / imageWidth
  const sy = drawHeight / imageHeight

  for (let y = 0; y < MODEL_SIZE; y++) {
    for (let x = 0; x < MODEL_SIZE; x++) {
      // 先把 512x512 座標映射回原始圖片座標
      const imgX = (x / MODEL_SIZE) * imageWidth
      const imgY = (y / MODEL_SIZE) * imageHeight

      // 再從圖片座標映射回畫布座標（考慮縮放與置中偏移）
      const canvasX = offsetX + imgX * sx
      const canvasY = offsetY + imgY * sy

      let alpha = 0
      if (
        canvasX >= 0 &&
        canvasX < canvas.width &&
        canvasY >= 0 &&
        canvasY < canvas.height
      ) {
        const cx = Math.floor(canvasX)
        const cy = Math.floor(canvasY)
        const idx = (cy * canvas.width + cx) * 4
        alpha = srcData[idx + 3]
      }

      const outIdx = (y * MODEL_SIZE + x) * 4
      // RGB 對遮罩不重要，全部設 0，alpha 帶入遮罩資訊
      outData[outIdx] = 0
      outData[outIdx + 1] = 0
      outData[outIdx + 2] = 0
      outData[outIdx + 3] = alpha
    }
  }

  return outImageData
}

defineExpose({
  getMaskImageData: getMaskImageDataInternal,
})

onMounted(() => {
  window.addEventListener('resize', resizeCanvasesToContainer)
  resizeCanvasesToContainer()
  drawImage()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvasesToContainer)
})

watch(
  () => editor.originalImageDataUrl,
  () => {
    resizeCanvasesToContainer()
  },
)

watch(
  () => props.clearTrigger,
  () => {
    clearMask()
  },
)
</script>

<template>
  <div
    ref="containerRef"
    class="relative flex-1 rounded-lg border border-slate-800 bg-slate-950/60 overflow-hidden"
  >
    <canvas
      ref="imageCanvasRef"
      class="absolute inset-0 w-full h-full"
    />
    <canvas
      ref="maskCanvasRef"
      class="absolute inset-0 w-full h-full cursor-crosshair"
      @pointerdown.prevent="onPointerDown"
      @pointermove.prevent="onPointerMove"
      @pointerup.prevent="onPointerUp"
      @pointerleave.prevent="onPointerUp"
    />
    <div
      v-if="!editor.originalImageDataUrl"
      class="absolute inset-0 flex items-center justify-center text-xs text-slate-500"
    >
      請先於上方選擇一張圖片
    </div>
  </div>
</template>

