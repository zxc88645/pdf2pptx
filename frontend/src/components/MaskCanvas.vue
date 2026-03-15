<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  width: { type: Number, default: 0 },
  height: { type: Number, default: 0 },
  brushSize: { type: Number, default: 20 },
})

const emit = defineEmits(['maskBlob'])

const canvasRef = ref(null)
const containerRef = ref(null)
/** 與顯示 canvas 同步的黑白遮罩（黑底白筆觸），匯出時直接 toBlob，無需整張掃描 */
const maskExportRef = ref(null)
const drawing = ref(false)

const MASK_EXPORT_MAX = 1024
const cursorScreen = ref({ x: 0, y: 0 })
const showBrushPreview = ref(false)

function getCtx() {
  const c = canvasRef.value
  return c ? c.getContext('2d') : null
}

/** 筆刷預覽：依 canvas object-contain 的實際顯示比例算出螢幕上的直徑，fixed 定位跟隨游標 */
const brushPreviewStyle = computed(() => {
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

function draw(e) {
  const ctx = getCtx()
  if (!ctx || !drawing.value) return
  const { x: clientX, y: clientY } = getClientPos(e)
  updateCursor(e)
  const d = getCanvasDisplayRect()
  if (!d) return
  // 滑鼠在「實際顯示區」內的座標 → 換算成 canvas 座標（object-contain 留白已扣除）
  const canvasX = (clientX - d.left) / d.scale
  const canvasY = (clientY - d.top) / d.scale
  // 僅在畫布範圍內繪製，避免拖出邊界時畫到錯位
  const x = Math.max(0, Math.min(props.width, canvasX))
  const y = Math.max(0, Math.min(props.height, canvasY))
  // 顯示用：醒目紅色半透明
  ctx.fillStyle = 'rgba(220, 38, 38, 0.75)'
  ctx.beginPath()
  ctx.arc(x, y, props.brushSize, 0, Math.PI * 2)
  ctx.fill()
  // 即時更新匯出用黑白遮罩（同位置畫白點），匯出時無需再掃整張圖
  const mask = maskExportRef.value
  if (mask?.width && mask?.height) {
    const size = getMaskExportSize()
    const mx = (x * size.width) / props.width
    const my = (y * size.height) / props.height
    const mr = Math.max(1, (props.brushSize * size.width) / props.width)
    const mCtx = mask.getContext('2d')
    mCtx.fillStyle = '#fff'
    mCtx.beginPath()
    mCtx.arc(mx, my, mr, 0, Math.PI * 2)
    mCtx.fill()
  }
}

function startDraw() {
  drawing.value = true
}

function endDraw() {
  drawing.value = false
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
