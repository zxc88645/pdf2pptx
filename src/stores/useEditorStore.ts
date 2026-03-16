import { defineStore } from 'pinia'
import { initSession, runInpainting } from '../services/inferenceService'

export interface EditorState {
  originalImageDataUrl: string | null
  resultImageDataUrl: string | null
  isModelLoading: boolean
  isInferencing: boolean
  errorMessage: string | null
}

export const useEditorStore = defineStore('editor', {
  state: (): EditorState => ({
    originalImageDataUrl: null,
    resultImageDataUrl: null,
    isModelLoading: false,
    isInferencing: false,
    errorMessage: null,
  }),
  actions: {
    setOriginalImage(dataUrl: string | null) {
      this.originalImageDataUrl = dataUrl
      this.resultImageDataUrl = null
      this.errorMessage = null
    },
    setResultImage(dataUrl: string | null) {
      this.resultImageDataUrl = dataUrl
    },
    setError(message: string | null) {
      this.errorMessage = message
    },
    setModelLoading(loading: boolean) {
      this.isModelLoading = loading
    },
    setInferencing(loading: boolean) {
      this.isInferencing = loading
    },
    async initModel(): Promise<void> {
      this.setError(null)
      this.setModelLoading(true)

      try {
        await initSession()
      } catch (err) {
        console.error(err)
        this.setError('模型載入失敗，請稍後再試或檢查模型檔是否存在')
      } finally {
        this.setModelLoading(false)
      }
    },
    async runInference(maskImageData: ImageData): Promise<void> {
      if (!this.originalImageDataUrl) {
        this.setError('請先選擇一張圖片')
        return
      }

      this.setError(null)
      this.setInferencing(true)

      try {
        const resultDataUrl = await runInpainting(this.originalImageDataUrl, maskImageData)
        this.setResultImage(resultDataUrl)
      } catch (err) {
        console.error(err)
        this.setError('推理失敗，請稍後再試或檢查模型設定')
      } finally {
        this.setInferencing(false)
      }
    },
  },
})

