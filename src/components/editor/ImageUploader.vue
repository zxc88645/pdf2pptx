<script setup lang="ts">
import { computed } from 'vue'
import { useEditorStore } from '../../stores/useEditorStore'

const editor = useEditorStore()

const hasImage = computed(() => !!editor.originalImageDataUrl)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!file.type.startsWith('image/')) {
    editor.setError('請選擇圖片檔案')
    return
  }

  const reader = new FileReader()
  reader.onload = () => {
    const dataUrl = reader.result as string
    editor.setOriginalImage(dataUrl)
  }
  reader.onerror = () => {
    editor.setError('讀取圖片失敗')
  }
  reader.readAsDataURL(file)
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <label
      class="relative flex items-center justify-between gap-3 rounded-lg border border-dashed border-slate-700 bg-slate-900/70 px-3 py-2 text-xs text-slate-400 hover:border-slate-500 transition-colors cursor-pointer"
    >
      <div class="flex items-center gap-2">
        <span
          class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-sky-500/15 text-sky-300 text-xs"
        >
          選
        </span>
        <div class="flex flex-col">
          <span class="font-medium text-slate-200">選擇圖片</span>
          <span class="text-[11px] text-slate-400">
            支援 PNG / JPG（不會上傳到伺服器）
          </span>
        </div>
      </div>
      <div
        v-if="hasImage"
        class="text-[11px] text-emerald-400 flex items-center gap-1"
      >
        <span class="h-1.5 w-1.5 rounded-full bg-emerald-400" /> 已載入
      </div>
      <input
        type="file"
        accept="image/*"
        class="absolute inset-0 opacity-0 cursor-pointer"
        @change="onFileChange"
      />
    </label>
  </div>
</template>

