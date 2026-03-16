<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useTheme } from '../composables/useTheme'

const route = useRoute()
const { theme, setTheme } = useTheme()
const themeMenuOpen = ref(false)

function closeMenu() {
  themeMenuOpen.value = false
}

onMounted(() => {
  document.addEventListener('click', closeMenu)
})
onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
})

const navItems = [
  { path: '/', label: 'PDF 轉 PPT', icon: 'doc' },
  { path: '/pdf-to-images', label: 'PDF 轉圖片', icon: 'docimg' },
  { path: '/images-to-pdf', label: '圖片轉 PDF', icon: 'imgdoc' },
  { path: '/ocr', label: '圖片辨識', icon: 'scan' },
  { path: '/inpaint', label: '智能抹除', icon: 'brush' },
]
</script>

<template>
  <div class="flex min-h-screen w-full">
    <!-- Sidebar: fixed left, dashboard style -->
    <aside
      class="shrink-0 w-56 sm:w-64 flex flex-col border-r border-gray-200 dark:border-[var(--dracula-surface)] bg-white dark:bg-[var(--dracula-surface)]"
    >
      <div class="p-4 sm:p-5 border-b border-gray-200 dark:border-[var(--dracula-comment)]/40">
        <RouterLink
          to="/"
          class="text-lg sm:text-xl font-bold text-gray-900 dark:text-[var(--dracula-foreground)] no-underline hover:text-primary dark:hover:text-[var(--dracula-cyan)] transition-colors"
        >
          PDF2PPT
        </RouterLink>
      </div>
      <nav class="flex-1 p-3 space-y-0.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium no-underline transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[var(--dracula-bg)]"
          :class="route.path === item.path
            ? 'bg-primary text-white dark:bg-[var(--dracula-purple)] dark:text-[var(--dracula-bg)] shadow-sm'
            : 'text-gray-600 dark:text-[var(--dracula-foreground)]/90 hover:bg-gray-100 dark:hover:bg-white/10 hover:text-gray-900 dark:hover:text-[var(--dracula-foreground)]'"
        >
          <span v-if="item.icon === 'doc'" class="w-5 h-5 shrink-0 flex items-center justify-center text-base">📄</span>
          <span v-else-if="item.icon === 'docimg'" class="w-5 h-5 shrink-0 flex items-center justify-center text-base">🖼</span>
          <span v-else-if="item.icon === 'imgdoc'" class="w-5 h-5 shrink-0 flex items-center justify-center text-base">📑</span>
          <span v-else-if="item.icon === 'scan'" class="w-5 h-5 shrink-0 flex items-center justify-center text-base">🔍</span>
          <span v-else class="w-5 h-5 shrink-0 flex items-center justify-center text-base">🖌</span>
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="p-3 border-t border-gray-200 dark:border-[var(--dracula-comment)]/40">
        <div class="relative" @click.stop>
          <button
            type="button"
            aria-haspopup="true"
            :aria-expanded="themeMenuOpen"
            aria-label="切換主題"
            class="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 dark:text-[var(--dracula-foreground)]/90 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[var(--dracula-bg)]"
            @click.stop="themeMenuOpen = !themeMenuOpen"
          >
            <span class="w-5 h-5 shrink-0 flex items-center justify-center">
              <svg v-if="theme === 'light'" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <svg v-else-if="theme === 'dark'" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </span>
            主題
          </button>
          <div
            v-show="themeMenuOpen"
            class="absolute left-0 bottom-full mb-1 w-full py-1.5 rounded-xl shadow-lg bg-white dark:bg-[var(--dracula-bg)] border border-gray-200 dark:border-[var(--dracula-comment)]/50 z-20"
          >
            <button
              type="button"
              class="w-full px-4 py-2.5 text-left text-sm flex items-center gap-3 text-gray-700 dark:text-[var(--dracula-foreground)] hover:bg-gray-100 dark:hover:bg-white/10 transition-colors first:rounded-t-xl last:rounded-b-xl"
              :class="{ 'bg-gray-100 dark:bg-white/10 font-medium': theme === 'light' }"
              @click="setTheme('light'); themeMenuOpen = false"
            >
              <span class="w-5 h-5 inline-flex items-center justify-center text-lg">☀</span>
              淺色
            </button>
            <button
              type="button"
              class="w-full px-4 py-2.5 text-left text-sm flex items-center gap-3 text-gray-700 dark:text-[var(--dracula-foreground)] hover:bg-gray-100 dark:hover:bg-white/10 transition-colors first:rounded-t-xl last:rounded-b-xl"
              :class="{ 'bg-gray-100 dark:bg-white/10 font-medium': theme === 'dark' }"
              @click="setTheme('dark'); themeMenuOpen = false"
            >
              <span class="w-5 h-5 inline-flex items-center justify-center text-lg">🌙</span>
              深色 (Dracula)
            </button>
            <button
              type="button"
              class="w-full px-4 py-2.5 text-left text-sm flex items-center gap-3 text-gray-700 dark:text-[var(--dracula-foreground)] hover:bg-gray-100 dark:hover:bg-white/10 transition-colors first:rounded-t-xl last:rounded-b-xl"
              :class="{ 'bg-gray-100 dark:bg-white/10 font-medium': theme === 'system' }"
              @click="setTheme('system'); themeMenuOpen = false"
            >
              <span class="w-5 h-5 inline-flex items-center justify-center text-lg">💻</span>
              跟隨系統
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main content: scrollable dashboard area -->
    <div class="flex-1 flex flex-col min-w-0">
      <header class="shrink-0 px-4 sm:px-6 lg:px-8 py-5 sm:py-6 border-b border-gray-200 dark:border-[var(--dracula-comment)]/40 bg-white/80 dark:bg-[var(--dracula-bg)]/80 backdrop-blur-sm">
        <p class="text-sm sm:text-base text-gray-600 dark:text-[var(--dracula-comment)] max-w-2xl leading-relaxed">
          將純圖片 PDF 轉成可編輯簡報、圖片辨識文字，或上傳圖片圈選要抹除的區域。
        </p>
      </header>
      <main class="flex-1 overflow-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 bg-gray-50/50 dark:bg-[var(--dracula-bg)]">
        <RouterView />
      </main>
    </div>
  </div>
</template>
