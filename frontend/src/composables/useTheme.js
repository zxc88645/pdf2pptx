import { ref, watch, onMounted } from 'vue'

const STORAGE_KEY = 'theme'

/** @type {'light'|'dark'|'system'} */
function getStored() {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'light' || v === 'dark' || v === 'system') return v
  } catch (_) {}
  return 'system'
}

function prefersDark() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function getEffective(theme) {
  if (theme === 'light') return 'light'
  if (theme === 'dark') return 'dark'
  return prefersDark() ? 'dark' : 'light'
}

function applyToDocument(effective) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  if (effective === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export function useTheme() {
  const theme = ref(getStored())

  function setTheme(value) {
    if (value !== 'light' && value !== 'dark' && value !== 'system') return
    theme.value = value
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch (_) {}
    applyToDocument(getEffective(value))
  }

  watch(theme, (value) => {
    applyToDocument(getEffective(value))
  }, { immediate: false })

  onMounted(() => {
    applyToDocument(getEffective(theme.value))
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', () => {
      if (theme.value === 'system') applyToDocument(getEffective('system'))
    })
  })

  return {
    theme,
    setTheme,
    effective: () => getEffective(theme.value),
  }
}
