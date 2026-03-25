import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * PDF 抹除工作流程狀態：每頁的「套用結果」與「最新抹除結果」由 store 統一管理，
 * 換頁後再切回來仍會保留該頁的套用狀態。
 */
export const usePdfInpaintStore = defineStore('pdfInpaint', () => {
  /** 各頁已套用的底圖：pageNum (1-based) -> Blob */
  const appliedByPage = ref({})
  /** 各頁最新抹除結果（用於顯示「抹除結果」區與匯出）：pageNum -> Blob */
  const resultByPage = ref({})
  /** 各頁畫布尺寸（PdfViewer 回傳），顯示已套用圖時沿用該頁尺寸 */
  const dimensionsByPage = ref({})
  /** 各頁遮罩快照（顯示層與匯出層），供切頁後還原 */
  const maskSnapshotByPage = ref({})
  /** 各頁 OCR 區塊、錯誤與已選取區塊 */
  const ocrStateByPage = ref({})

  function setDimensions(pageNum, width, height) {
    if (width && height) dimensionsByPage.value[pageNum] = { width, height }
  }

  function getDimensions(pageNum) {
    return dimensionsByPage.value[pageNum] ?? null
  }

  function setApplied(pageNum, blob) {
    if (blob) appliedByPage.value[pageNum] = blob
  }

  function getApplied(pageNum) {
    return appliedByPage.value[pageNum] ?? null
  }

  function setResult(pageNum, blob) {
    if (blob) resultByPage.value[pageNum] = blob
  }

  function getResult(pageNum) {
    return resultByPage.value[pageNum] ?? null
  }

  function setMaskSnapshot(pageNum, snapshot) {
    if (snapshot?.overlayDataUrl && snapshot?.maskDataUrl) {
      maskSnapshotByPage.value[pageNum] = snapshot
    }
  }

  function getMaskSnapshot(pageNum) {
    return maskSnapshotByPage.value[pageNum] ?? null
  }

  function clearMaskSnapshot(pageNum) {
    delete maskSnapshotByPage.value[pageNum]
  }

  function ensureOcrState(pageNum) {
    if (!ocrStateByPage.value[pageNum]) {
      ocrStateByPage.value[pageNum] = {
        items: [],
        error: '',
        selectedIds: [],
      }
    }
    return ocrStateByPage.value[pageNum]
  }

  function setOcrItems(pageNum, items) {
    const state = ensureOcrState(pageNum)
    state.items = Array.isArray(items) ? items : []
    state.error = ''
    state.selectedIds = state.selectedIds.filter((id) => state.items.some((item) => item.id === id))
  }

  function getOcrItems(pageNum) {
    return ensureOcrState(pageNum).items
  }

  function setOcrError(pageNum, error) {
    const state = ensureOcrState(pageNum)
    state.error = error || ''
  }

  function getOcrError(pageNum) {
    return ensureOcrState(pageNum).error
  }

  function setSelectedOcrIds(pageNum, ids) {
    ensureOcrState(pageNum).selectedIds = Array.isArray(ids) ? ids : []
  }

  function getSelectedOcrIds(pageNum) {
    return ensureOcrState(pageNum).selectedIds
  }

  function clearOcrState(pageNum) {
    delete ocrStateByPage.value[pageNum]
  }

  /** 更換 PDF 檔案時呼叫，清空所有頁面的套用／結果與尺寸，避免與新檔混淆 */
  function clearAll() {
    appliedByPage.value = {}
    resultByPage.value = {}
    dimensionsByPage.value = {}
    maskSnapshotByPage.value = {}
    ocrStateByPage.value = {}
  }

  /** 目前有套用或結果的頁碼集合，供匯出多頁時使用 */
  const pageNumbersWithContent = computed(() => {
    const set = new Set([
      ...Object.keys(appliedByPage.value).map(Number),
      ...Object.keys(resultByPage.value).map(Number),
    ])
    return Array.from(set).sort((a, b) => a - b)
  })

  return {
    appliedByPage,
    resultByPage,
    dimensionsByPage,
    maskSnapshotByPage,
    ocrStateByPage,
    setDimensions,
    getDimensions,
    setApplied,
    getApplied,
    setResult,
    getResult,
    setMaskSnapshot,
    getMaskSnapshot,
    clearMaskSnapshot,
    setOcrItems,
    getOcrItems,
    setOcrError,
    getOcrError,
    setSelectedOcrIds,
    getSelectedOcrIds,
    clearOcrState,
    clearAll,
    pageNumbersWithContent,
  }
})
