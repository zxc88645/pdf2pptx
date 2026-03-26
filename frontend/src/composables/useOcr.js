import { ref } from 'vue'
import { createDefaultPPOcrV5 } from 'ffocr'

const ocrInstance = createDefaultPPOcrV5({ cacheModels: true })

/** 辨識框向外擴展的像素數（各邊） */
const OCR_BOX_PADDING = 2

function normalizeResult(raw) {
  if (!raw || !Array.isArray(raw.lines)) return []
  return raw.lines
    .map((line, idx) => {
      const points = line.box?.points
      if (!points || points.length < 4) return null
      const xs = points.map((p) => p.x)
      const ys = points.map((p) => p.y)
      const minX = Math.min(...xs) - OCR_BOX_PADDING
      const maxX = Math.max(...xs) + OCR_BOX_PADDING
      const minY = Math.min(...ys) - OCR_BOX_PADDING
      const maxY = Math.max(...ys) + OCR_BOX_PADDING
      return {
        id: `ocr-${idx}`,
        text: line.text ?? '',
        rect: {
          x: Math.max(0, minX),
          y: Math.max(0, minY),
          width: Math.max(1, maxX - Math.max(0, minX)),
          height: Math.max(1, maxY - Math.max(0, minY)),
        },
      }
    })
    .filter(Boolean)
}

export function useOcr() {
  const loading = ref(false)
  const error = ref('')

  async function recognizeFromBlob(blob) {
    if (!blob) return []
    loading.value = true
    error.value = ''
    try {
      const raw = await ocrInstance.ocr(blob)
      return normalizeResult(raw)
    } catch (e) {
      error.value = e?.message || String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    recognizeFromBlob,
  }
}
