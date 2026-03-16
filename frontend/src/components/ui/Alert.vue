<script setup>
defineProps({
  variant: { type: String, default: 'error' },
})
</script>

<template>
  <div
    role="alert"
    class="mt-4 px-4 py-3 rounded-lg text-sm"
    :class="{
      'bg-red-50 dark:bg-[var(--dracula-red)]/15 text-red-800 dark:text-[var(--dracula-red)] border border-red-200 dark:border-[var(--dracula-red)]/50': variant === 'error',
      'bg-amber-50 dark:bg-[var(--dracula-orange)]/15 text-amber-800 dark:text-[var(--dracula-orange)] border border-amber-200 dark:border-[var(--dracula-orange)]/50': variant === 'warning',
      'bg-green-50 dark:bg-[var(--dracula-green)]/15 text-green-800 dark:text-[var(--dracula-green)] border border-green-200 dark:border-[var(--dracula-green)]/50': variant === 'success',
    }"
  >
    <slot />
  </div>
</template>
