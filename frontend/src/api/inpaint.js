/**
 * 從圖片 blob 取得實際寬高（用於確保 mask 與底圖尺寸一致）
 * @param {Blob|File} imageBlob
 * @returns {Promise<{ width: number, height: number }>}
 */
async function getImageDimensions(imageBlob) {
  const bitmap = await createImageBitmap(imageBlob)
  const width = bitmap.width
  const height = bitmap.height
  bitmap.close()
  return { width, height }
}

/**
 * 將 mask blob 縮放至指定尺寸，確保與底圖一致，避免 "images do not match" 錯誤
 * @param {Blob|File} maskBlob
 * @param {number} targetWidth
 * @param {number} targetHeight
 * @returns {Promise<Blob>}
 */
async function resizeMaskToDimensions(maskBlob, targetWidth, targetHeight) {
  const maskBitmap = await createImageBitmap(maskBlob)
  const canvas = new OffscreenCanvas(targetWidth, targetHeight)
  const ctx = canvas.getContext('2d')
  ctx.drawImage(maskBitmap, 0, 0, targetWidth, targetHeight)
  maskBitmap.close()
  return canvas.convertToBlob({ type: 'image/png', compressLevel: 1 })
}

/**
 * 上傳 image 與 mask，取得 inpainting 結果圖（PNG blob）。
 * 會自動依底圖實際尺寸調整 mask，避免後端 "images do not match" 錯誤。
 * @param {Blob|File} imageBlob
 * @param {Blob|File} maskBlob
 * @returns {Promise<Blob>}
 */
export async function inpaint(imageBlob, maskBlob) {
  const { width: imgW, height: imgH } = await getImageDimensions(imageBlob)
  const resizedMask = await resizeMaskToDimensions(maskBlob, imgW, imgH)

  const form = new FormData()
  form.append('image', imageBlob, 'image.png')
  form.append('mask', resizedMask, 'mask.png')
  const baseURL = import.meta.env.VITE_API_BASE || ''
  const url = baseURL ? `${baseURL}/api/inpaint` : '/api/inpaint'
  const res = await fetch(url, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.blob()
}
