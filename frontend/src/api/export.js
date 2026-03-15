const baseURL = import.meta.env.VITE_API_BASE || ''

function apiUrl(path) {
  return baseURL ? `${baseURL}${path}` : path
}

/**
 * 多張圖片 → 下載 PDF
 * @param {Blob[]} imageBlobs
 * @returns {Promise<Blob>}
 */
export async function exportPdf(imageBlobs) {
  const form = new FormData()
  imageBlobs.forEach((blob, i) => form.append('files', blob, `page_${i}.png`))
  const res = await fetch(apiUrl('/api/export/pdf'), {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)
  return res.blob()
}

/**
 * 原 PDF + 替換頁索引 + 該頁 mask → 後端做 inpainting 並組合成新 PDF
 * @param {File} pdfFile
 * @param {number} pageIndex 0-based
 * @param {Blob} maskBlob
 * @returns {Promise<Blob>}
 */
export async function exportPdfFromPdf(pdfFile, pageIndex, maskBlob) {
  const form = new FormData()
  form.append('pdf', pdfFile)
  form.append('replace_page_index', String(pageIndex))
  form.append('mask', maskBlob, 'mask.png')
  const res = await fetch(apiUrl('/api/export/pdf-from-pdf'), {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)
  return res.blob()
}

/**
 * 多張圖片 → 下載 PPTX
 * @param {Blob[]} imageBlobs
 * @returns {Promise<Blob>}
 */
export async function exportPpt(imageBlobs) {
  const form = new FormData()
  imageBlobs.forEach((blob, i) => form.append('files', blob, `slide_${i}.png`))
  const res = await fetch(apiUrl('/api/export/ppt'), {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)
  return res.blob()
}

/**
 * 完整頁面匯出：PDF + 替換頁（0-based 索引 → Blob），匯出為單一 PDF
 * @param {File} pdfFile
 * @param {Record<number, Blob>} replacements 頁索引 (0-based) → 該頁替換圖
 * @returns {Promise<Blob>}
 */
export async function exportPdfFull(pdfFile, replacements = {}) {
  const form = new FormData()
  form.append('pdf', pdfFile)
  for (const [index, blob] of Object.entries(replacements)) {
    if (blob) form.append('replacement', blob, `page_${index}.png`)
  }
  const res = await fetch(apiUrl('/api/export/pdf-full'), {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)
  return res.blob()
}

/**
 * 完整頁面匯出：PDF + 替換頁，匯出為單一 PPTX
 */
export async function exportPptFull(pdfFile, replacements = {}) {
  const form = new FormData()
  form.append('pdf', pdfFile)
  for (const [index, blob] of Object.entries(replacements)) {
    if (blob) form.append('replacement', blob, `page_${index}.png`)
  }
  const res = await fetch(apiUrl('/api/export/ppt-full'), {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)
  return res.blob()
}

/**
 * 完整頁面匯出：PDF + 替換頁，匯出為 PNG 壓縮檔
 */
export async function exportPngZipFull(pdfFile, replacements = {}) {
  const form = new FormData()
  form.append('pdf', pdfFile)
  for (const [index, blob] of Object.entries(replacements)) {
    if (blob) form.append('replacement', blob, `page_${index}.png`)
  }
  const res = await fetch(apiUrl('/api/export/png-zip-full'), {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)
  return res.blob()
}
