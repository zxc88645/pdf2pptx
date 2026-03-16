<script setup lang="ts">
const props = defineProps<{
  canRun: boolean
  isInferencing: boolean
}>()

const emit = defineEmits<{
  clearMask: []
  runInference: []
}>()
</script>

<template>
  <div
    class="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-xs"
  >
    <div class="flex items-center gap-2 text-[11px] text-slate-400">
      <span class="text-slate-300 font-medium">畫筆</span>
      <span class="inline-flex items-center gap-1">
        <span class="h-1.5 w-1.5 rounded-full bg-sky-400" /> 遮罩顏色：白
      </span>
      <span class="hidden sm:inline-block text-slate-500">
        左鍵塗抹要移除的區域
      </span>
    </div>

    <div class="flex items-center gap-2">
      <button
        type="button"
        class="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800 disabled:opacity-50 disabled:hover:bg-transparent"
        @click="emit('clearMask')"
      >
        清除遮罩
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-1 rounded-md border border-sky-500/60 bg-sky-500/20 px-3 py-1 text-[11px] font-medium text-sky-100 hover:bg-sky-500/30 disabled:opacity-50 disabled:hover:bg-sky-500/20"
        :disabled="!props.canRun || props.isInferencing"
        @click="emit('runInference')"
      >
        <span
          v-if="props.isInferencing"
          class="h-3 w-3 rounded-full border-2 border-sky-200 border-t-transparent animate-spin"
        />
        <span v-else class="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        <span>{{ props.isInferencing ? '推理中...' : '執行抹除' }}</span>
      </button>
    </div>
  </div>
</template>

