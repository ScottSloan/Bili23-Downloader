<script setup>
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()

defineProps({
  text: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <label class="fluent-label" :class="themeStore.theme">{{ text }}</label>
</template>

<style scoped>
.fluent-label {
  display: block;
  transition: color 0.2s ease;
  user-select: none;
}

.fluent-label.light {
  color: black;
}

.fluent-label.dark {
  color: white;
}
</style>
