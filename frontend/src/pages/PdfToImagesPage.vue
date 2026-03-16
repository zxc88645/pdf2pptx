<script setup>
import { ref } from 'vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Select from '../components/ui/Select.vue'
import Alert from '../components/ui/Alert.vue'

const file = ref(null)
const loading = ref(false)
const error = ref('')
const format = ref('png')
const dpi = ref(150)

const formatOptions = [
  { value: 'png', label: 'PNG' },
  { value: 'jpg', label: 'JPG' },
]

async function convert() {
  if (!file.value?.files?.[0]) {
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
    const params = new URLSearchParams({
      format: format.value,
      dpi: String(dpi.value),
    })
    const res = await fetch(`/api/pdf-to-images?${params}`, {
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
      'pdf_pages.zip'
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
      PDF 轉圖片
    </h1>
    <p class="text-gray-600 dark:text-[var(--dracula-comment)] mb-6">
      將 PDF 每一頁轉成 PNG 或 JPG 圖片，以 ZIP 壓縮檔下載。
    </p>
    <Card>
      <div class="space-y-4">
        <label class="flex flex-wrap items-center gap-2 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]">
          輸出格式：
          <Select v-model="format" :disabled="loading">
            <option v-for="opt in formatOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </Select>
        </label>
        <label class="flex flex-col gap-1 text-sm text-gray-700 dark:text-[var(--dracula-foreground)]">
          DPI（解析度，72–300）：
          <div class="flex items-center gap-3">
            <input
              v-model.number="dpi"
              type="range"
              min="72"
              max="300"
              step="10"
              :disabled="loading"
              class="w-full"
            />
            <span class="w-12 text-right tabular-nums">{{ dpi }}</span>
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
          <Button variant="primary" :loading="loading" @click="convert">
            {{ loading ? '轉換中…' : '上傳並轉換' }}
          </Button>
        </div>
      </div>
    </Card>
    <Alert v-if="error" variant="error">{{ error }}</Alert>
  </div>
</template>
