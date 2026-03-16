<script setup>
import { ref, onBeforeUnmount } from 'vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Alert from '../components/ui/Alert.vue'

const fileInput = ref(null)
const items = ref([])
const loading = ref(false)
const error = ref('')
const dragIndex = ref(null)

const ACCEPT = 'image/png,image/jpeg,image/jpg,image/webp'

function revokeAll() {
  items.value.forEach((it) => URL.revokeObjectURL(it.url))
  items.value = []
}

function onFileChange(event) {
  revokeAll()
  error.value = ''
  const files = event.target.files
  if (!files || !files.length) return
  const list = []
  for (let i = 0; i < files.length; i++) {
    const f = files[i]
    if (!f.type.startsWith('image/')) {
      error.value = `請只選擇圖片檔案：${f.name}`
      return
    }
    list.push({ file: f, url: URL.createObjectURL(f) })
  }
  items.value = list
}

function onDragStart(e, index) {
  dragIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(index))
  e.target.classList.add('opacity-50', 'cursor-grabbing')
}

function onDragEnd(e) {
  dragIndex.value = null
  e.target.classList.remove('opacity-50', 'cursor-grabbing')
}

function onDragOver(e) {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
}

function onDrop(e, dropIndex) {
  e.preventDefault()
  const from = dragIndex.value
  if (from == null || from === dropIndex) return
  const arr = [...items.value]
  const [removed] = arr.splice(from, 1)
  arr.splice(dropIndex, 0, removed)
  items.value = arr
  dragIndex.value = null
  e.target.classList.remove('opacity-50', 'cursor-grabbing')
}

function removeItem(index) {
  URL.revokeObjectURL(items.value[index].url)
  items.value = items.value.filter((_, i) => i !== index)
}

async function convert() {
  if (!items.value.length) {
    error.value = '請選擇至少一張圖片'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const form = new FormData()
    items.value.forEach((it) => form.append('files', it.file))
    const res = await fetch('/api/images-to-pdf', {
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
      'output.pdf'
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

onBeforeUnmount(revokeAll)
</script>

<template>
  <div class="max-w-6xl mx-auto text-left">
    <h1 class="text-xl font-semibold text-gray-900 dark:text-[var(--dracula-foreground)] mb-2">
      圖片轉 PDF
    </h1>
    <p class="text-gray-600 dark:text-[var(--dracula-comment)] mb-6">
      將多張圖片（PNG、JPG、WebP）合併成一個 PDF，可拖曳調整頁面順序。
    </p>
    <Card>
      <div class="space-y-4">
        <div class="flex flex-col gap-3">
          <input
            ref="fileInput"
            type="file"
            :accept="ACCEPT"
            multiple
            :disabled="loading"
            class="block w-full text-sm text-gray-900 dark:text-[var(--dracula-foreground)] file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary file:text-white file:cursor-pointer file:disabled:opacity-60"
            @change="onFileChange"
          />
          <Button variant="primary" :loading="loading" @click="convert">
            {{ loading ? '轉換中…' : '上傳並轉換' }}
          </Button>
        </div>
        <div
          v-if="items.length"
          class="pt-2 border-t border-gray-200 dark:border-[var(--dracula-comment)]/40"
        >
          <p class="text-sm text-gray-500 dark:text-[var(--dracula-comment)] mb-2">
            拖曳圖片可調整 PDF 頁面順序
          </p>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="(it, i) in items"
              :key="it.url"
              draggable="true"
              class="group relative w-20 h-20 rounded overflow-hidden border-2 border-gray-200 dark:border-[var(--dracula-comment)]/50 bg-gray-100 dark:bg-[var(--dracula-surface)] cursor-grab hover:border-primary dark:hover:border-[var(--dracula-cyan)] transition-colors select-none"
              :class="{ 'ring-2 ring-primary ring-offset-1 dark:ring-offset-[var(--dracula-bg)]': dragIndex === i }"
              @dragstart="onDragStart($event, i)"
              @dragend="onDragEnd"
              @dragover="onDragOver"
              @drop="onDrop($event, i)"
            >
              <img
                :src="it.url"
                :alt="`預覽 ${i + 1}`"
                class="w-full h-full object-contain pointer-events-none"
                draggable="false"
              />
              <span
                class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs text-center py-0.5"
              >
                {{ i + 1 }}
              </span>
              <button
                type="button"
                class="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-red-500/90 text-white text-xs flex items-center justify-center hover:bg-red-600 transition-opacity opacity-70 hover:opacity-100"
                aria-label="移除"
                @click.stop="removeItem(i)"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      </div>
    </Card>
    <Alert v-if="error" variant="error">{{ error }}</Alert>
  </div>
</template>
