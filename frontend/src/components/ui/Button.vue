<script setup>
import Spinner from './Spinner.vue'

defineProps({
  variant: { type: String, default: 'primary' },
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    class="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none disabled:opacity-70 disabled:cursor-not-allowed"
    :class="{
      'bg-primary text-white hover:bg-primary-hover dark:bg-[var(--dracula-purple)] dark:text-[var(--dracula-bg)] dark:hover:bg-[var(--dracula-cyan)] dark:hover:text-[var(--dracula-bg)]': variant === 'primary',
      'bg-gray-200 dark:bg-[var(--dracula-surface)] text-gray-800 dark:text-[var(--dracula-foreground)] hover:bg-gray-300 dark:hover:bg-[var(--dracula-comment)]/40': variant === 'secondary',
      'bg-transparent text-gray-700 dark:text-[var(--dracula-foreground)] hover:bg-black/5 dark:hover:bg-white/10': variant === 'ghost',
    }"
  >
    <Spinner v-if="loading" size="sm" class="shrink-0" />
    <slot />
  </button>
</template>
