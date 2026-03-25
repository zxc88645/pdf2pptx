import { ref } from 'vue'
import * as ocr from '@paddlejs-models/ocr'

function flattenNumbers(value, out = []) {
  if (Array.isArray(value)) {
    for (const item of value) flattenNumbers(item, out)
  } else if (typeof value === 'number' && Number.isFinite(value)) {
    out.push(value)
  }
  return out
}

function pointsToRect(points) {
  const nums = flattenNumbers(points)
  if (nums.length < 4) return null
  const xs = []
  const ys = []
  for (let i = 0; i < nums.length; i += 2) {
    xs.push(nums[i])
    ys.push(nums[i + 1])
  }
  if (!xs.length || !ys.length) return null
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  }
}

function normalizeResult(raw) {
  if (!raw) return []
  const pointsList = Array.isArray(raw.points) ? raw.points : []
  const textList = Array.isArray(raw.text) ? raw.text : []
  return pointsList
    .map((pts, idx) => {
      const rect = pointsToRect(pts)
      if (!rect) return null
      return {
        id: `ocr-${idx}`,
        text: typeof textList[idx] === 'string' ? textList[idx] : '',
        rect,
      }
    })
    .filter(Boolean)
}

function blobToImage(blob) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = (e) => {
      URL.revokeObjectURL(url)
      reject(e)
    }
    img.src = url
  })
}

export function useOcr() {
  const inited = ref(false)
  const loading = ref(false)
  const error = ref('')

  async function ensureInit() {
    if (inited.value) return
    await ocr.init()
    inited.value = true
  }

  async function recognizeFromBlob(blob) {
    if (!blob) return []
    loading.value = true
    error.value = ''
    try {
      await ensureInit()
      const img = await blobToImage(blob)
      const raw = await ocr.recognize(img)
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
