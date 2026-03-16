<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useEditorStore } from './stores/useEditorStore'
import ImageUploader from './components/editor/ImageUploader.vue'
import CanvasEditor from './components/editor/CanvasEditor.vue'
import Toolbar from './components/editor/Toolbar.vue'
import ResultPanel from './components/editor/ResultPanel.vue'

const editor = useEditorStore()
const { originalImageDataUrl, isInferencing, isModelLoading, errorMessage } = storeToRefs(editor)

const clearTrigger = ref(0)
const canvasRef = ref<InstanceType<typeof CanvasEditor> | null>(null)

async function handleRunInference() {
  const mask = canvasRef.value?.getMaskImageData()
  if (!mask) {
    editor.setError('尚未在畫布上塗抹遮罩')
    return
  }
  await editor.runInference(mask)
}

function handleClearMask() {
  clearTrigger.value++
}

onMounted(() => {
  editor.initModel()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-slate-950 text-slate-50">
    <header class="border-b border-slate-900 bg-slate-950/95 backdrop-blur">
      <div class="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div
            class="h-9 w-9 rounded-lg bg-sky-500/10 border border-sky-400/40 flex items-center justify-center text-sky-300 font-semibold text-lg"
          >
            La
          </div>
          <div>
            <h1 class="text-lg font-semibold tracking-tight">
              LaMa Inpainting Studio
            </h1>
            <p class="text-xs text-slate-400">
              Vue + Tailwind + Pinia · 瀏覽器端 ONNX 推理
            </p>
          </div>
        </div>
        <div class="hidden sm:flex items-center gap-3 text-xs text-slate-400">
          <span class="inline-flex items-center gap-1">
            <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            本地執行 · 不上傳圖片
          </span>
        </div>
      </div>
    </header>

    <main class="flex-1">
      <div class="mx-auto max-w-6xl px-4 py-6 flex flex-col gap-3">
        <div v-if="errorMessage" class="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          {{ errorMessage }}
        </div>

        <div
          class="grid gap-4 lg:gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]"
        >
          <section
            class="rounded-xl border border-slate-900 bg-slate-900/80 backdrop-blur-sm shadow-sm shadow-slate-950/40 p-4 flex flex-col gap-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <h2 class="text-sm font-semibold tracking-tight">
                  編輯與遮罩
                </h2>
                <p class="text-xs text-slate-400">
                  選擇圖片並在畫布上塗抹想要移除的區域
                </p>
              </div>
            </div>

            <ImageUploader />

            <Toolbar
              :can-run="!!originalImageDataUrl"
              :is-inferencing="isInferencing"
              @run-inference="handleRunInference"
              @clear-mask="handleClearMask"
            />

            <CanvasEditor ref="canvasRef" :clear-trigger="clearTrigger" />
          </section>

          <section
            class="rounded-xl border border-slate-900 bg-slate-900/80 backdrop-blur-sm shadow-sm shadow-slate-950/40 p-4 flex flex-col gap-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <h2 class="text-sm font-semibold tracking-tight">
                  結果預覽
                </h2>
                <p class="text-xs text-slate-400">
                  完成推理後，可在此區比較前後差異
                </p>
              </div>
            </div>

            <ResultPanel />
          </section>
        </div>
      </div>
    </main>

    <div
      v-if="isModelLoading"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur"
    >
      <div class="w-[90%] max-w-sm rounded-xl border border-slate-800 bg-slate-900 px-6 py-5 shadow-xl shadow-black/60">
        <div class="flex items-center gap-3">
          <div
            class="h-8 w-8 rounded-full border-2 border-sky-300/70 border-t-transparent animate-spin"
          />
          <div>
            <p class="text-sm font-medium text-slate-50">
              正在下載並載入模型…
            </p>
            <p class="mt-1 text-xs text-slate-400">
              第一次載入可能需要一點時間，請稍候不要關閉此頁面。
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


