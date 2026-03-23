import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ command }) => {
  // 讓 GitHub Pages（專案頁面通常是 `/<repo>/`）能正確載入靜態資源。
  // 本機 dev 時維持 `/`，避免影響 `npm run dev`。
  const base =
    command === 'build'
      ? (process.env.VITE_BASE_PATH || '/')
      : '/'

  return {
    base,
    plugins: [vue()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
