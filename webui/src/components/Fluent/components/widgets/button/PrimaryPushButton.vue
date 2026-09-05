<script setup lang="ts">
import pushButton from './PushButton.vue'

defineProps(['title'])
</script>

<template>
  <pushButton :title="title" variant="primary" />
</template>

<style scoped>
.fluent-button.light.is-primary {
  background-color: var(--primary-color);
  border: 1px solid var(--primary-color-light-1);
  border-bottom: 1px solid var(--primary-color-dark-1);
  color: white;
}

.fluent-button.light.is-primary:hover {
  background-color: var(--primary-color-light-1);
  border: 1px solid var(--primary-color-light-2);
  border-bottom: 1px solid var(--primary-color-dark-1);
}

.fluent-button.light.is-primary:active {
  background-color: var(--primary-color-light-3);
  border: 1px solid var(--primary-color-light-3);
  color: rgba(255, 255, 255, 0.63);
}

.fluent-button.dark.is-primary {
  background-color: var(--primary-color);
  border: 1px solid var(--primary-color-light-1);
  border-bottom: 1px solid var(--primary-color-light-2);
  color: black;
}

.fluent-button.dark.is-primary:hover {
  background-color: var(--primary-color-dark-1);
  border: 1px solid var(--primary-color-light-1);
  border-bottom: 1px solid var(--primary-color-light-2);
}

.fluent-button.dark.is-primary:active {
  background-color: var(--primary-color-dark-2);
  border: 1px solid var(--primary-color-dark-2);
  color: rgba(0, 0, 0, 0.63);
}
</style>
