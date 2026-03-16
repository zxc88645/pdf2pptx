<script setup>
import { ref } from 'vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Select from '../components/ui/Select.vue'
import Alert from '../components/ui/Alert.vue'

const file = ref(null)
const loading = ref(false)
const error = ref('')
const backend = ref('lama')
const debug = ref(false)
// OCR 最小信心分數（0~1），提高可以減少圖標/雜訊文字
const ocrMinScore = ref(0.9)

async function upload() {
  if (!file.value || !file.value.files || !file.value.files[0]) {
    error.value = '請選擇一個 PDF 檔案'
    return
  }
  const f = file.value.files[0]
  if (!f.name.toLowerCase().endsWith('.pdf')) {
    error.value = '請選擇 PDF 檔案（.pdf）'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const form = new FormData()
    form.append('file', f)
    const backendParam = encodeURIComponent(backend.value || 'lama')
    const debugParam = debug.value ? '&debug=true' : ''
    const ocrParam = `&ocr_min_score=${encodeURIComponent(String(ocrMinScore.value))}`
    const res = await fetch(`/api/convert?backend=${backendParam}${debugParam}${ocrParam}`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const t = await res.text()
      throw new Error(t || `HTTP ${res.status}`)
    }
    const blob = await res.blob()
    const name =
      res.headers.get('Content-Disposition')?.match(/filename=(.+)/)?.[1]?.trim() ||
      'output.pptx'
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = name.replace(/^["']|["']$/g, '')
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    error.value = e.message || '轉換失敗'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto text-left">
    <h1 class="text-xl font-semibold text-gray-900 dark:text-[var(--dracula-foreground)] mb-2">
      PDF 轉可編輯 PPT
    </h1>
    <p class="text-gray-600 dark:text-[var(--dracula-comment)] mb-6">
      上傳純圖 PDF，取得可編輯的 PowerPoint 檔案。
    </p>
    <Card>
      <div class="space-y-4">
        <label class="flex flex-wrap items-center gap-2 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]">
          抹除文字後端：
          <Select v-model="backend" :disabled="loading">
            <option value="lama">LaMa（推薦，較少亂碼）</option>
            <option value="sd">Stable Diffusion</option>
          </Select>
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]">
          <input
            v-model="debug"
            type="checkbox"
            :disabled="loading"
            class="rounded border-gray-300 dark:border-[var(--dracula-comment)] text-primary focus:ring-primary"
          />
          啟用 debug（轉出的 PPT 會將 OCR 文字區塊框起來）
        </label>
        <label
          class="flex flex-col gap-1 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]"
        >
          OCR 最小信心分數（越高越少雜訊文字）：
          <div class="flex items-center gap-3">
            <input
              v-model.number="ocrMinScore"
              type="range"
              min="0.3"
              max="0.95"
              step="0.05"
              :disabled="loading"
              class="w-full"
            />
            <span class="w-12 text-right tabular-nums">{{ ocrMinScore.toFixed(2) }}</span>
          </div>
        </label>
        <div class="flex flex-col gap-3">
          <input
            ref="file"
            type="file"
            accept=".pdf,application/pdf"
            :disabled="loading"
            class="block w-full text-sm text-gray-900 dark:text-[var(--dracula-foreground)] file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary file:text-white file:cursor-pointer file:disabled:opacity-60"
          />
          <Button variant="primary" :loading="loading" @click="upload">
            {{ loading ? '轉換中…' : '上傳並轉換' }}
          </Button>
        </div>
      </div>
    </Card>
    <Alert v-if="error" variant="error">{{ error }}</Alert>
  </div>
</template>
