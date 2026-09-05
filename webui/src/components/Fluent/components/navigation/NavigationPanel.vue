<script setup lang="ts">
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()
</script>

<template>
  <div class="navigation-panel" :class="themeStore.theme">
    <slot />
  </div>
</template>

<style scoped>
.navigation-panel {
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-right: none;
  border-bottom: none;
  border-top-left-radius: 10px;
  box-sizing: border-box;
}

.navigation-panel.light {
  border: 1px solid rgba(0, 0, 0, 0.068);
  background-color: rgba(255, 255, 255, 0.5);
}

.navigation-panel.dark {
  border: 1px solid rgba(0, 0, 0, 0.18);
  background-color: rgba(255, 255, 255, 0.0314);
}
</style>
