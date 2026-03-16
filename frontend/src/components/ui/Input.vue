<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  disabled: { type: Boolean, default: false },
  id: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <input
    :id="id"
    :type="type"
    :value="modelValue"
    :disabled="disabled"
    class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-[var(--dracula-comment)]/50 bg-white dark:bg-[var(--dracula-surface)] text-gray-900 dark:text-[var(--dracula-foreground)] placeholder-gray-500 dark:placeholder-[var(--dracula-comment)] focus:ring-2 focus:ring-primary dark:focus:ring-[var(--dracula-cyan)] focus:border-primary focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
    @input="emit('update:modelValue', $event.target.value)"
  />
</template>
