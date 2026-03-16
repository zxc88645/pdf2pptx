<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  disabled: { type: Boolean, default: false },
  id: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <select
    :id="id"
    :value="modelValue"
    :disabled="disabled"
    class="px-3 py-2 rounded-lg border border-gray-300 dark:border-[var(--dracula-comment)]/50 bg-white dark:bg-[var(--dracula-surface)] text-gray-900 dark:text-[var(--dracula-foreground)] focus:ring-2 focus:ring-primary dark:focus:ring-[var(--dracula-cyan)] focus:border-primary focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
    @change="emit('update:modelValue', $event.target.value)"
  >
    <slot />
  </select>
</template>
