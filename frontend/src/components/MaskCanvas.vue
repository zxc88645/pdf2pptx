<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  width: { type: Number, default: 0 },
  height: { type: Number, default: 0 },
  brushSize: { type: Number, default: 20 },
  /** 'brush' | 'eraser' | 'rectangle' | 'rectangleBatch' */
  mode: { type: String, default: 'brush' },
})

const emit = defineEmits(['maskBlob', 'rectCommit'])

const canvasRef = ref(null)
const containerRef = ref(null)
/** 與顯示 canvas 同步的黑白遮罩（黑底白筆觸），匯出時直接 toBlob，無需整張掃描 */
const maskExportRef = ref(null)
const drawing = ref(false)
/** 框選模式：拖曳起點（canvas 座標） */
const rectStart = ref(null)
/** 框選模式：拖曳目前點（canvas 座標） */
const rectCurrent = ref(null)
const previewCanvasRef = ref(null)

const MASK_EXPORT_MAX = 1024
const cursorScreen = ref({ x: 0, y: 0 })
const showBrushPreview = ref(false)

function getCtx() {
  const c = canvasRef.value
  return c ? c.getContext('2d') : null
}

function loadImageFromDataUrl(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = dataUrl
  })
}

/** 筆刷預覽：依 canvas object-contain 的實際顯示比例算出螢幕上的直徑，fixed 定位跟隨游標（僅筆刷模式） */
const brushPreviewStyle = computed(() => {
  if (props.mode !== 'brush' && props.mode !== 'eraser') return {}
  const d = getCanvasDisplayRect()
  if (!d) return {}
  const diameterPx = Math.max(4, Math.round(2 * props.brushSize * d.scale))
  return {
    position: 'fixed',
    width: `${diameterPx}px`,
    height: `${diameterPx}px`,
    left: `${cursorScreen.value.x - diameterPx / 2}px`,
    top: `${cursorScreen.value.y - diameterPx / 2}px`,
    pointerEvents: 'none',
  }
})

/** 顯示用：清成透明，讓底下的 PDF 預覽可見 */
function clearToTransparent() {
  const ctx = getCtx()
  if (!ctx) return
  ctx.clearRect(0, 0, props.width, props.height)
  const mask = maskExportRef.value
  if (mask?.width && mask?.height) {
    const mCtx = mask.getContext('2d')
    mCtx.fillStyle = '#000'
    mCtx.fillRect(0, 0, mask.width, mask.height)
  }
  clearPreviewRect()
}

/** 取得遮罩 canvas 的尺寸與縮放比（匯出用，最長邊不超過 MASK_EXPORT_MAX） */
function getMaskExportSize() {
  const w = props.width || 0
  const h = props.height || 0
  if (!w || !h) return null
  const scale =
    w <= MASK_EXPORT_MAX && h <= MASK_EXPORT_MAX
      ? 1
      : Math.min(MASK_EXPORT_MAX / w, MASK_EXPORT_MAX / h, 1)
  return {
    width: Math.round(w * scale),
    height: Math.round(h * scale),
    scaleX: scale,
    scaleY: scale,
  }
}

/** 確保 maskExportRef 存在且尺寸正確，並清成黑底 */
function ensureMaskExportCanvas() {
  const size = getMaskExportSize()
  if (!size || !size.width || !size.height) return
  let mask = maskExportRef.value
  if (!mask || mask.width !== size.width || mask.height !== size.height) {
    mask = document.createElement('canvas')
    mask.width = size.width
    mask.height = size.height
    maskExportRef.value = mask
  }
  const ctx = mask.getContext('2d')
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, mask.width, mask.height)
}

/**
 * 取得 canvas 在 object-contain 下的「實際顯示區」。
 * 當圖片較高/較寬時，畫布會留白，滑鼠座標必須對應到顯示區而非整個元素框。
 */
function getCanvasDisplayRect() {
  const c = canvasRef.value
  if (!c?.width || !c?.height) return null
  const rect = c.getBoundingClientRect()
  const cw = c.width
  const ch = c.height
  const scale = Math.min(rect.width / cw, rect.height / ch)
  const displayW = cw * scale
  const displayH = ch * scale
  const offsetX = (rect.width - displayW) / 2
  const offsetY = (rect.height - displayH) / 2
  return {
    left: rect.left + offsetX,
    top: rect.top + offsetY,
    width: displayW,
    height: displayH,
    scale,
  }
}

/** 從滑鼠或觸控事件取得螢幕座標 */
function getClientPos(e) {
  if (e.touches?.length) {
    return { x: e.touches[0].clientX, y: e.touches[0].clientY }
  }
  return { x: e.clientX, y: e.clientY }
}

function updateCursor(e) {
  const rect = containerRef.value?.getBoundingClientRect()
  if (!rect) return
  const { x, y } = getClientPos(e)
  cursorScreen.value = { x, y }
  showBrushPreview.value = x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom
}

function toCanvasCoords(clientX, clientY) {
  const d = getCanvasDisplayRect()
  if (!d) return null
  const canvasX = (clientX - d.left) / d.scale
  const canvasY = (clientY - d.top) / d.scale
  return {
    x: Math.max(0, Math.min(props.width, canvasX)),
    y: Math.max(0, Math.min(props.height, canvasY)),
  }
}

function draw(e) {
  const { x: clientX, y: clientY } = getClientPos(e)
  updateCursor(e)
  const pt = toCanvasCoords(clientX, clientY)
  if (!pt) return

  if (props.mode === 'rectangle' || props.mode === 'rectangleBatch') {
    if (drawing.value) {
      rectCurrent.value = { x: pt.x, y: pt.y }
      drawPreviewRect()
    }
    return
  }

  const ctx = getCtx()
  if (!ctx || !drawing.value) return
  const { x, y } = pt
  const isEraser = props.mode === 'eraser'
  if (isEraser) {
    ctx.save()
    ctx.globalCompositeOperation = 'destination-out'
    ctx.beginPath()
    ctx.arc(x, y, props.brushSize, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  } else {
    // 顯示用：醒目紅色半透明
    ctx.fillStyle = 'rgba(220, 38, 38, 0.75)'
    ctx.beginPath()
    ctx.arc(x, y, props.brushSize, 0, Math.PI * 2)
    ctx.fill()
  }
  // 即時更新匯出用黑白遮罩（同位置畫白點），匯出時無需再掃整張圖
  const mask = maskExportRef.value
  if (mask?.width && mask?.height) {
    const size = getMaskExportSize()
    const mx = (x * size.width) / props.width
    const my = (y * size.height) / props.height
    const mr = Math.max(1, (props.brushSize * size.width) / props.width)
    const mCtx = mask.getContext('2d')
    if (isEraser) {
      mCtx.save()
      mCtx.globalCompositeOperation = 'destination-out'
      mCtx.beginPath()
      mCtx.arc(mx, my, mr, 0, Math.PI * 2)
      mCtx.fill()
      mCtx.restore()
      mCtx.save()
      mCtx.globalCompositeOperation = 'destination-over'
      mCtx.fillStyle = '#000'
      mCtx.fillRect(0, 0, mask.width, mask.height)
      mCtx.restore()
    } else {
      mCtx.fillStyle = '#fff'
      mCtx.beginPath()
      mCtx.arc(mx, my, mr, 0, Math.PI * 2)
      mCtx.fill()
    }
  }
}

function startDraw(e) {
  drawing.value = true
  if (props.mode === 'rectangle' || props.mode === 'rectangleBatch') {
    const pt = toCanvasCoords(getClientPos(e).x, getClientPos(e).y)
    if (pt) rectStart.value = { x: pt.x, y: pt.y }
    rectCurrent.value = null
  }
}

/** 由框選拖曳取得正規化矩形（canvas 座標），過小則回傳 null */
function getRectFromDrag() {
  const start = rectStart.value
  const current = rectCurrent.value
  if (!start || !current) return null
  const x1 = Math.min(start.x, current.x)
  const y1 = Math.min(start.y, current.y)
  const w = Math.abs(current.x - start.x)
  const h = Math.abs(current.y - start.y)
  if (w < 2 || h < 2) return null
  return { x: x1, y: y1, width: Math.max(1, w), height: Math.max(1, h) }
}

function endDraw() {
  if (
    (props.mode === 'rectangle' || props.mode === 'rectangleBatch') &&
    drawing.value &&
    rectStart.value &&
    rectCurrent.value
  ) {
    if (props.mode === 'rectangle') {
      commitRect()
    } else {
      const r = getRectFromDrag()
      if (r) emit('rectCommit', r)
    }
    clearPreviewRect()
    rectStart.value = null
    rectCurrent.value = null
  }
  drawing.value = false
}

/** 框選預覽：在預覽 canvas 上畫出目前拖曳的矩形 */
function drawPreviewRect() {
  const p = previewCanvasRef.value
  const start = rectStart.value
  const current = rectCurrent.value
  if (!p || !start || !current) return
  const ctx = p.getContext('2d')
  ctx.clearRect(0, 0, props.width, props.height)
  const x1 = Math.min(start.x, current.x)
  const y1 = Math.min(start.y, current.y)
  const w = Math.abs(current.x - start.x)
  const h = Math.abs(current.y - start.y)
  if (w < 2 && h < 2) return
  const batch = props.mode === 'rectangleBatch'
  ctx.fillStyle = batch ? 'rgba(14, 165, 233, 0.35)' : 'rgba(220, 38, 38, 0.5)'
  ctx.strokeStyle = batch ? 'rgba(2, 132, 199, 0.95)' : 'rgba(220, 38, 38, 0.95)'
  ctx.lineWidth = 2
  ctx.fillRect(x1, y1, w, h)
  ctx.strokeRect(x1, y1, w, h)
}

function clearPreviewRect() {
  const p = previewCanvasRef.value
  if (p) p.getContext('2d')?.clearRect(0, 0, props.width, props.height)
}

/** 將框選矩形寫入顯示 canvas 與匯出遮罩 */
function commitRect() {
  const start = rectStart.value
  const current = rectCurrent.value
  if (!start || !current) return
  const x1 = Math.min(start.x, current.x)
  const y1 = Math.min(start.y, current.y)
  const w = Math.max(1, Math.abs(current.x - start.x))
  const h = Math.max(1, Math.abs(current.y - start.y))
  const ctx = getCtx()
  if (ctx) {
    ctx.fillStyle = 'rgba(220, 38, 38, 0.75)'
    ctx.fillRect(x1, y1, w, h)
  }
  const mask = maskExportRef.value
  if (mask?.width && mask?.height) {
    const size = getMaskExportSize()
    const mx1 = (x1 * size.width) / props.width
    const my1 = (y1 * size.height) / props.height
    const mw = Math.max(1, (w * size.width) / props.width)
    const mh = Math.max(1, (h * size.height) / props.height)
    const mCtx = mask.getContext('2d')
    mCtx.fillStyle = '#fff'
    mCtx.fillRect(mx1, my1, mw, mh)
  }
}

function emitMask() {
  const mask = maskExportRef.value
  if (!mask?.width || !mask?.height) return
  mask.toBlob((blob) => emit('maskBlob', blob), 'image/png', 1)
}

watch(
  () => [props.width, props.height],
  () => {
    if (props.width && props.height) {
      const c = canvasRef.value
      if (c) {
        c.width = props.width
        c.height = props.height
        clearToTransparent()
        ensureMaskExportCanvas()
      }
      const p = previewCanvasRef.value
      if (p) {
        p.width = props.width
        p.height = props.height
        p.getContext('2d')?.clearRect(0, 0, props.width, props.height)
      }
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (canvasRef.value && props.width && props.height) {
    canvasRef.value.width = props.width
    canvasRef.value.height = props.height
    clearToTransparent()
    ensureMaskExportCanvas()
  }
  if (previewCanvasRef.value && props.width && props.height) {
    previewCanvasRef.value.width = props.width
    previewCanvasRef.value.height = props.height
  }
  window.addEventListener('mouseup', endDraw)
  window.addEventListener('touchend', endDraw)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', endDraw)
  window.removeEventListener('touchend', endDraw)
})

function clearMask() {
  clearToTransparent()
  emitMask()
}

defineExpose({
  getMaskBlob() {
    return new Promise((resolve) => {
      const mask = maskExportRef.value
      if (!mask?.width || !mask?.height) {
        resolve(null)
        return
      }
      mask.toBlob((blob) => resolve(blob), 'image/png', 1)
    })
  },
  removeRectMask(rect) {
    const x = Number(rect?.x ?? 0)
    const y = Number(rect?.y ?? 0)
    const w = Number(rect?.width ?? 0)
    const h = Number(rect?.height ?? 0)
    if (w <= 0 || h <= 0) return
    const x1 = Math.max(0, Math.min(props.width, x))
    const y1 = Math.max(0, Math.min(props.height, y))
    const x2 = Math.max(0, Math.min(props.width, x + w))
    const y2 = Math.max(0, Math.min(props.height, y + h))
    const cw = Math.max(1, x2 - x1)
    const ch = Math.max(1, y2 - y1)
    const ctx = getCtx()
    if (ctx) {
      ctx.save()
      ctx.globalCompositeOperation = 'destination-out'
      ctx.fillStyle = 'rgba(0, 0, 0, 1)'
      ctx.fillRect(x1, y1, cw, ch)
      ctx.restore()
    }
    const mask = maskExportRef.value
    if (mask?.width && mask?.height) {
      const size = getMaskExportSize()
      const mx = (x1 * size.width) / props.width
      const my = (y1 * size.height) / props.height
      const mw = Math.max(1, (cw * size.width) / props.width)
      const mh = Math.max(1, (ch * size.height) / props.height)
      const mCtx = mask.getContext('2d')
      mCtx.fillStyle = '#000'
      mCtx.fillRect(mx, my, mw, mh)
    }
  },
  applyRectMask(rect) {
    const x = Number(rect?.x ?? 0)
    const y = Number(rect?.y ?? 0)
    const w = Number(rect?.width ?? 0)
    const h = Number(rect?.height ?? 0)
    if (w <= 0 || h <= 0) return
    const x1 = Math.max(0, Math.min(props.width, x))
    const y1 = Math.max(0, Math.min(props.height, y))
    const x2 = Math.max(0, Math.min(props.width, x + w))
    const y2 = Math.max(0, Math.min(props.height, y + h))
    const cw = Math.max(1, x2 - x1)
    const ch = Math.max(1, y2 - y1)
    const ctx = getCtx()
    if (ctx) {
      ctx.fillStyle = 'rgba(220, 38, 38, 0.75)'
      ctx.fillRect(x1, y1, cw, ch)
    }
    const mask = maskExportRef.value
    if (mask?.width && mask?.height) {
      const size = getMaskExportSize()
      const mx = (x1 * size.width) / props.width
      const my = (y1 * size.height) / props.height
      const mw = Math.max(1, (cw * size.width) / props.width)
      const mh = Math.max(1, (ch * size.height) / props.height)
      const mCtx = mask.getContext('2d')
      mCtx.fillStyle = '#fff'
      mCtx.fillRect(mx, my, mw, mh)
    }
  },
  exportMaskSnapshot() {
    const overlay = canvasRef.value
    const mask = maskExportRef.value
    if (!overlay?.width || !overlay?.height || !mask?.width || !mask?.height) return null
    return {
      overlayDataUrl: overlay.toDataURL('image/png'),
      maskDataUrl: mask.toDataURL('image/png'),
    }
  },
  async importMaskSnapshot(snapshot) {
    const overlay = canvasRef.value
    const mask = maskExportRef.value
    if (!overlay || !mask) return
    clearToTransparent()
    if (!snapshot?.overlayDataUrl || !snapshot?.maskDataUrl) return
    const [overlayImg, maskImg] = await Promise.all([
      loadImageFromDataUrl(snapshot.overlayDataUrl),
      loadImageFromDataUrl(snapshot.maskDataUrl),
    ])
    const oCtx = overlay.getContext('2d')
    const mCtx = mask.getContext('2d')
    oCtx.clearRect(0, 0, overlay.width, overlay.height)
    oCtx.drawImage(overlayImg, 0, 0, overlay.width, overlay.height)
    mCtx.fillStyle = '#000'
    mCtx.fillRect(0, 0, mask.width, mask.height)
    mCtx.drawImage(maskImg, 0, 0, mask.width, mask.height)
  },
  clearMask,
  emitMask,
})
</script>

<template>
  <div
    ref="containerRef"
    class="absolute inset-0 cursor-crosshair touch-none"
    @mousemove="updateCursor"
    @mouseenter="(e) => { updateCursor(e); showBrushPreview = true }"
    @mouseleave="showBrushPreview = false"
  >
    <!-- 遮罩畫布：紅色半透明，底下 PDF 可透出，塗抹處一目了然 -->
    <canvas
      ref="canvasRef"
      class="block w-full h-full object-contain mask-canvas-overlay"
      :width="width"
      :height="height"
      @mousedown="startDraw"
      @mousemove="draw"
      @touchstart.passive="startDraw"
      @touchmove.prevent="draw"
    />
    <!-- 框選預覽層：拖曳時顯示矩形預覽，與主 canvas 同尺寸疊加 -->
    <canvas
      v-show="mode === 'rectangle' || mode === 'rectangleBatch'"
      ref="previewCanvasRef"
      class="absolute inset-0 w-full h-full object-contain pointer-events-none mask-canvas-overlay"
      :width="width"
      :height="height"
    />
    <!-- 筆刷預覽：Teleport 到 body 避免被外層 transform 影響，才能與實際滑鼠對齊 -->
    <Teleport to="body">
      <div
        v-show="showBrushPreview && !drawing"
        class="mask-canvas-brush-preview"
        :style="brushPreviewStyle"
        aria-hidden="true"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.mask-canvas-overlay {
  opacity: 0.9;
}
.mask-canvas-overlay:hover {
  opacity: 1;
}
</style>
<style>
/* 筆刷預覽在 body 下，需全域樣式；pointer-events: none 不擋操作 */
.mask-canvas-brush-preview {
  position: fixed;
  border: 2px solid rgba(220, 38, 38, 0.95);
  border-radius: 50%;
  pointer-events: none;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.8);
  z-index: 9999;
}
</style>
