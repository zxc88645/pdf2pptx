<script setup>
import { ref, shallowRef, watch, nextTick, onBeforeUnmount } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.mjs?url'
import { storeToRefs } from 'pinia'
import { usePdfInpaintStore } from '../stores/pdfInpaint'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

const props = defineProps({
  file: { type: File, default: null },
  currentPage: { type: Number, default: 1 },
  thumbnailScale: { type: Number, default: 0.25 },
  maxThumbWidth: { type: Number, default: 240 },
})

const emit = defineEmits(['select-page'])

const store = usePdfInpaintStore()
const { appliedByPage } = storeToRefs(store)
/** 各頁已套用圖的 object URL，用於左側縮圖顯示 */
const appliedThumbUrls = ref({})

// 頁面比例 485 × 271 公釐（橫向）
const PAGE_ASPECT_RATIO = 485 / 271

const pdfDoc = shallowRef(null)
const totalPages = ref(0)
const loading = ref(false)
const thumbnails = ref([]) // { pageNum, dataUrl }

async function loadPdf(file) {
  if (!file) {
    pdfDoc.value = null
    totalPages.value = 0
    thumbnails.value = []
    return
  }
  loading.value = true
  try {
    const data = await file.arrayBuffer()
    const doc = await pdfjsLib.getDocument({ data }).promise
    pdfDoc.value = doc
    totalPages.value = doc.numPages
    await renderAllThumbnails(doc)
  } catch (e) {
    console.error(e)
    pdfDoc.value = null
    totalPages.value = 0
    thumbnails.value = []
  } finally {
    loading.value = false
  }
}

async function renderAllThumbnails(doc) {
  const list = []
  for (let i = 1; i <= doc.numPages; i++) {
    try {
      const page = await doc.getPage(i)
      const viewport = page.getViewport({ scale: props.thumbnailScale })
      const canvas = document.createElement('canvas')
      canvas.width = viewport.width
      canvas.height = viewport.height
      const ctx = canvas.getContext('2d')
      await page.render({
        canvasContext: ctx,
        viewport,
      }).promise
      const dataUrl = canvas.toDataURL('image/png')
      list.push({ pageNum: i, dataUrl })
    } catch (e) {
      console.error('Thumbnail page', i, e)
    }
  }
  thumbnails.value = list
}

function syncAppliedThumbUrls() {
  const next = {}
  const prev = appliedThumbUrls.value
  for (const [pageNumStr, blob] of Object.entries(appliedByPage.value)) {
    const pageNum = Number(pageNumStr)
    if (prev[pageNum]) URL.revokeObjectURL(prev[pageNum])
    if (blob) next[pageNum] = URL.createObjectURL(blob)
  }
  for (const [pageNumStr, url] of Object.entries(prev)) {
    if (!(Number(pageNumStr) in next)) URL.revokeObjectURL(url)
  }
  appliedThumbUrls.value = next
}

watch(
  appliedByPage,
  () => syncAppliedThumbUrls(),
  { deep: true, immediate: true }
)

onBeforeUnmount(() => {
  for (const url of Object.values(appliedThumbUrls.value)) {
    URL.revokeObjectURL(url)
  }
  appliedThumbUrls.value = {}
})

watch(
  () => props.file,
  async (file) => {
    await loadPdf(file || null)
  },
  { immediate: true }
)
</script>

<template>
  <div class="space-y-2">
    <label v-if="totalPages > 0" class="block text-sm font-medium text-slate-700">頁面</label>
    <div v-if="loading" class="text-sm text-slate-500">載入縮圖…</div>
    <div
      v-else-if="thumbnails.length > 0"
      class="flex flex-col gap-2 max-h-[40vh] overflow-y-auto pr-1"
    >
      <button
        v-for="t in thumbnails"
        :key="t.pageNum"
        type="button"
        class="flex-shrink-0 w-full rounded border-2 transition-colors text-left overflow-hidden focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 bg-slate-100 flex flex-col"
        :class="currentPage === t.pageNum ? 'border-slate-600 bg-slate-50 ring-1 ring-slate-600' : 'border-slate-200 hover:border-slate-400 hover:bg-slate-50'"
        :style="{ maxWidth: maxThumbWidth + 'px' }"
        @click="emit('select-page', t.pageNum)"
      >
        <!-- 固定 485:271 比例容器，避免小圖變形 -->
        <div
          class="w-full flex-shrink-0 relative bg-slate-200"
          :style="{ aspectRatio: PAGE_ASPECT_RATIO }"
        >
          <img
            :src="appliedThumbUrls[t.pageNum] || t.dataUrl"
            :alt="'第 ' + t.pageNum + ' 頁'"
            class="absolute inset-0 w-full h-full object-contain object-center"
          />
        </div>
        <span class="block text-xs text-slate-600 py-1 px-2 bg-white/80">
          第 {{ t.pageNum }} 頁
        </span>
      </button>
    </div>
  </div>
</template>
