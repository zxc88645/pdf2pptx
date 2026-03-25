import './emscripten-module-polyfill.js'
import './map-getorinsert-polyfill.js'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
