<script setup>
import { toasts } from '../composables/useToast'

function remove(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}
</script>

<template>
  <div
    class="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
    aria-live="polite"
  >
    <TransitionGroup
      name="toast"
      tag="div"
      class="flex flex-col gap-2"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg min-w-[240px] max-w-[360px]"
        :class="
          t.type === 'success'
            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
            : 'border-red-200 bg-red-50 text-red-800'
        "
      >
        <span
          v-if="t.type === 'success'"
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white text-xs"
          aria-hidden
        >
          ✓
        </span>
        <span
          v-else
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-500 text-white text-xs"
          aria-hidden
        >
          !
        </span>
        <p class="flex-1 text-sm font-medium">{{ t.message }}</p>
        <button
          type="button"
          class="shrink-0 rounded p-1 opacity-70 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-offset-1"
          :class="t.type === 'success' ? 'hover:bg-emerald-200/50' : 'hover:bg-red-200/50'"
          aria-label="關閉"
          @click="remove(t.id)"
        >
          <span class="sr-only">關閉</span>
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(1rem);
}
.toast-move {
  transition: transform 0.25s ease;
}
</style>
