<script setup lang="ts">
defineProps({
  text: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <label class="fluent-label">{{ text }}</label>
</template>

<style scoped>
.fluent-label {
  display: block;
  color: var(--text-primary);
  transition: color 0.2s ease;
  user-select: none;
}
</style>
