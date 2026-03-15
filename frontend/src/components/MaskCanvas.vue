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
const drawing = ref(false)
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
  // 使用醒目紅色半透明顯示，匯出時會轉成黑底白遮罩給 API
  ctx.fillStyle = 'rgba(220, 38, 38, 0.75)'
  ctx.beginPath()
  ctx.arc(x, y, props.brushSize, 0, Math.PI * 2)
  ctx.fill()
}

function startDraw() {
  drawing.value = true
}

function endDraw() {
  drawing.value = false
}

function emitMask() {
  const c = canvasRef.value
  if (!c || !c.width || !c.height) return
  c.toBlob(
    (blob) => emit('maskBlob', blob),
    'image/png',
    1
  )
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

// 匯出遮罩時若尺寸過大，先以較小尺寸計算再交給 inpaint API 端 resize，可大幅減少 getImageData/迴圈/PNG 編碼時間
const MASK_EXPORT_MAX = 1024

defineExpose({
  getMaskBlob() {
    return new Promise((resolve) => {
      const c = canvasRef.value
      if (!c || !c.width || !c.height) {
        resolve(null)
        return
      }
      const w = c.width
      const h = c.height
      const scale =
        w <= MASK_EXPORT_MAX && h <= MASK_EXPORT_MAX
          ? 1
          : Math.min(MASK_EXPORT_MAX / w, MASK_EXPORT_MAX / h, 1)
      const outW = Math.round(w * scale)
      const outH = Math.round(h * scale)
      // 匯出時轉成黑底白遮罩：有塗抹處（任意非透明）→ 白，其餘 → 黑（API 需要）
      const off = document.createElement('canvas')
      off.width = outW
      off.height = outH
      const ctx = off.getContext('2d')
      let imgData
      if (scale < 1) {
        ctx.drawImage(c, 0, 0, w, h, 0, 0, outW, outH)
        imgData = ctx.getImageData(0, 0, outW, outH)
      } else {
        imgData = c.getContext('2d').getImageData(0, 0, outW, outH)
      }
      const data = imgData.data
      const out = ctx.createImageData(outW, outH)
      const outData = out.data
      const threshold = 32
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]
        const a = data[i + 3]
        const isMask = a >= threshold || (r > threshold || g > threshold || b > threshold)
        const v = isMask ? 255 : 0
        outData[i] = outData[i + 1] = outData[i + 2] = v
        outData[i + 3] = 255
      }
      ctx.putImageData(out, 0, 0)
      off.toBlob((blob) => resolve(blob), 'image/png', 1)
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
