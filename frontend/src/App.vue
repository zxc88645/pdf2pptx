<template>
  <div class="app">
    <header class="header">
      <h1>PDF → 可編輯 PPT 轉換</h1>
      <p class="subtitle">上傳純圖檔 PDF，產出可編輯的 PowerPoint 簡報</p>
    </header>

    <main class="main">
      <section v-if="!jobId" class="upload-section">
        <div
          class="dropzone"
          :class="{ dragover: isDragover, uploading: uploading }"
          @dragover.prevent="isDragover = true"
          @dragleave.prevent="isDragover = false"
          @drop.prevent="onDrop"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".pdf,application/pdf"
            @change="onFileSelect"
          />
          <p v-if="!uploading">拖曳 PDF 至此，或點擊選擇檔案</p>
          <p v-else>上傳中…</p>
        </div>
        <p v-if="uploadError" class="error">{{ uploadError }}</p>
      </section>

      <section v-else class="status-section">
        <p class="job-id">任務 ID：<code>{{ jobId }}</code></p>
        <div class="status-box" :class="statusClass">
          <span class="status-label">狀態</span>
          <span class="status-value">{{ statusText }}</span>
          <span v-if="progress" class="progress">{{ progress }}</span>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions">
          <a
            v-if="downloadUrl"
            :href="downloadUrl"
            download="output.pptx"
            class="btn btn-primary"
          >
            下載 PPT
          </a>
          <button v-if="status === 'completed' || status === 'failed'" type="button" class="btn" @click="reset">
            再轉換一個
          </button>
        </div>
      </section>
    </main>

    <footer class="footer">
      <p>僅支援 PDF 上傳，單檔建議 50MB 以內</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const API_BASE = '/api'

const fileInput = ref(null)
const isDragover = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const jobId = ref('')
const status = ref('')
const progress = ref('')
const error = ref('')
const downloadUrl = ref('')

let pollTimer = null

const statusText = computed(() => {
  const map = {
    pending: '排隊中',
    splitting: '拆頁中',
    ocr: 'OCR 辨識中',
    inpainting: '去字與合成中',
    assembling: '組裝 PPT 中',
    completed: '完成',
    failed: '失敗',
  }
  return map[status.value] || status.value
})

const statusClass = computed(() => ({
  completed: status.value === 'completed',
  failed: status.value === 'failed',
}))

async function uploadFile(file) {
  if (!file || file.type !== 'application/pdf') {
    uploadError.value = '請選擇 PDF 檔案'
    return
  }
  uploadError.value = ''
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/jobs`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const t = await res.text()
      throw new Error(t || `上傳失敗 ${res.status}`)
    }
    const data = await res.json()
    jobId.value = data.job_id
    status.value = 'pending'
    progress.value = ''
    error.value = ''
    downloadUrl.value = ''
  } catch (e) {
    uploadError.value = e.message || '上傳失敗'
  } finally {
    uploading.value = false
  }
}

function onDrop(e) {
  isDragover.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

function onFileSelect(e) {
  const file = e.target?.files?.[0]
  if (file) uploadFile(file)
  if (fileInput.value) fileInput.value.value = ''
}

async function pollJob() {
  if (!jobId.value) return
  try {
    const res = await fetch(`${API_BASE}/jobs/${jobId.value}`)
    if (!res.ok) return
    const data = await res.json()
    status.value = data.status
    progress.value = data.progress || ''
    error.value = data.error || ''
    if (data.download_url) {
      downloadUrl.value = data.download_url
    }
    if (data.status === 'completed' || data.status === 'failed') {
      if (pollTimer) clearInterval(pollTimer)
      pollTimer = null
      return
    }
  } catch (_) {}
}

watch(jobId, (id) => {
  if (pollTimer) clearInterval(pollTimer)
  if (!id) return
  pollJob()
  pollTimer = setInterval(pollJob, 2000)
})

function reset() {
  jobId.value = ''
  status.value = ''
  progress.value = ''
  error.value = ''
  downloadUrl.value = ''
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  background: #1a1a2e;
  color: #eee;
  min-height: 100vh;
}
.app {
  max-width: 560px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  text-align: center;
  margin-bottom: 2rem;
}
.header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
}
.subtitle {
  color: #888;
  font-size: 0.9rem;
  margin: 0;
}
.main {
  flex: 1;
}
.upload-section,
.status-section {
  background: #16213e;
  border-radius: 12px;
  padding: 2rem;
  border: 1px solid #0f3460;
}
.dropzone {
  border: 2px dashed #0f3460;
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.dropzone.dragover {
  border-color: #e94560;
  background: rgba(233, 69, 96, 0.08);
}
.dropzone.uploading {
  pointer-events: none;
  opacity: 0.8;
}
.dropzone input {
  display: none;
}
.dropzone p {
  margin: 0;
  color: #aaa;
}
.error {
  color: #e94560;
  font-size: 0.9rem;
  margin-top: 1rem;
}
.job-id {
  font-size: 0.85rem;
  color: #888;
  margin-bottom: 1rem;
}
.job-id code {
  background: #0f3460;
  padding: 0.2em 0.5em;
  border-radius: 4px;
}
.status-box {
  padding: 1rem 1.25rem;
  background: #0f3460;
  border-radius: 8px;
  margin-bottom: 1rem;
}
.status-box.completed {
  background: #0d4d2b;
}
.status-box.failed {
  background: #5c1a1a;
}
.status-label {
  display: block;
  font-size: 0.75rem;
  color: #888;
  margin-bottom: 0.25rem;
}
.status-value {
  font-weight: 600;
}
.progress {
  display: block;
  font-size: 0.85rem;
  color: #aaa;
  margin-top: 0.25rem;
}
.actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.25rem;
}
.btn {
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  border: none;
  font-size: 0.95rem;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  color: inherit;
  background: #0f3460;
  color: #eee;
}
.btn-primary {
  background: #e94560;
  color: #fff;
}
.btn:hover {
  opacity: 0.9;
}
.footer {
  text-align: center;
  padding: 2rem 0 0;
  font-size: 0.8rem;
  color: #666;
}
</style>
