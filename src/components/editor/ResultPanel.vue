<script setup lang="ts">
import { computed, ref } from 'vue'
import { useEditorStore } from '../../stores/useEditorStore'

const editor = useEditorStore()

const showResult = ref(true)

const hasResult = computed(() => !!editor.resultImageDataUrl)
</script>

<template>
  <div class="flex flex-col gap-3 h-[480px]">
    <div class="flex items-center justify-between gap-2 text-xs">
      <div class="inline-flex items-center gap-2">
        <button
          type="button"
          class="rounded-md px-2 py-1 text-[11px]"
          :class="
            !showResult
              ? 'bg-slate-800 text-slate-100'
              : 'bg-transparent text-slate-400 hover:text-slate-200'
          "
          @click="showResult = false"
        >
          原圖
        </button>
        <button
          type="button"
          class="rounded-md px-2 py-1 text-[11px]"
          :class="
            showResult
              ? 'bg-slate-800 text-slate-100'
              : 'bg-transparent text-slate-400 hover:text-slate-200'
          "
          @click="showResult = true"
        >
          結果
        </button>
      </div>

      <div class="text-[11px] text-slate-500">
        <span v-if="editor.isInferencing">推理中，請稍候...</span>
        <span v-else-if="hasResult">已產生結果，可以切換查看</span>
      </div>
    </div>

    <div
      class="flex-1 rounded-lg border border-slate-800 bg-slate-950/60 overflow-hidden flex items-center justify-center"
    >
      <template v-if="editor.originalImageDataUrl">
        <img
          v-if="!showResult || !editor.resultImageDataUrl"
          :src="editor.originalImageDataUrl"
          alt="原始圖片"
          class="max-h-full max-w-full object-contain"
        />
        <img
          v-else
          :src="editor.resultImageDataUrl"
          alt="抹除結果"
          class="max-h-full max-w-full object-contain"
        />
      </template>
      <p v-else class="text-xs text-slate-500">
        尚未選擇圖片與執行推理。
      </p>
    </div>
  </div>
</template>

