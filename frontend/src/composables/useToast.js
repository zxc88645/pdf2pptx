import { ref } from 'vue'

const toasts = ref([])
const DEFAULT_DURATION = 3000

/**
 * 顯示 Toast 通知（純 Tailwind 樣式）
 * @param {string} message - 訊息內容
 * @param {'success'|'error'} [type='success'] - 類型
 * @param {number} [duration] - 顯示毫秒，預設 3000
 */
export function useToast() {
  function show(message, type = 'success', duration = DEFAULT_DURATION) {
    const id = Date.now() + Math.random()
    toasts.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => {
        toasts.value = toasts.value.filter((t) => t.id !== id)
      }, duration)
    }
    return id
  }

  function success(message, duration = DEFAULT_DURATION) {
    return show(message, 'success', duration)
  }

  function error(message, duration = DEFAULT_DURATION) {
    return show(message, 'error', duration)
  }

  return { toasts, show, success, error }
}

export { toasts }
