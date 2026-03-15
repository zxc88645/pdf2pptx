import { api } from './client'

/**
 * 上傳 image 與 mask，取得 inpainting 結果圖（PNG blob）
 * @param {Blob|File} imageBlob
 * @param {Blob|File} maskBlob
 * @returns {Promise<Blob>}
 */
export async function inpaint(imageBlob, maskBlob) {
  const form = new FormData()
  form.append('image', imageBlob, 'image.png')
  form.append('mask', maskBlob, 'mask.png')
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
