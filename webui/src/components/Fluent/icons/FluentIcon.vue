<script setup lang="ts">
import { computed } from 'vue'
import { FLUENT_ICONS } from './fluentIcons'

const props = defineProps<{
  name?: string
}>()

const icon = computed(() => (props.name ? FLUENT_ICONS[props.name] : undefined))
</script>

<template>
  <svg
    v-if="icon"
    class="fluent-icon"
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="icon.viewBox"
    aria-hidden="true"
    focusable="false"
    v-html="icon.body">
  </svg>
</template>

<style scoped>
.fluent-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  color: var(--text-primary);
}
</style>
