<script setup>
defineProps({
  title: { type: String, default: '' },
  class: { type: String, default: '' },
})
</script>

<template>
  <section
    class="rounded-xl border border-gray-200 dark:border-[var(--dracula-comment)]/50 bg-white dark:bg-[var(--dracula-surface)] p-4 sm:p-6 shadow-sm dark:shadow-none"
    :class="$props.class"
  >
    <h3
      v-if="title"
      class="text-base font-medium text-gray-900 dark:text-[var(--dracula-foreground)] mb-3"
    >
      {{ title }}
    </h3>
    <slot />
  </section>
</template>
