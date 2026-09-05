<script setup lang="ts">
import { IconApp } from '@/components/Fluent/icons'
</script>

<template>
  <div class="title-bar">
    <IconApp />
    <span>Bili23 Downloader</span>
  </div>
</template>

<style scoped>
.title-bar {
  min-height: 48px;
  display: flex;
  flex-direction: row;
  align-items: center;
  color: var(--text-primary);
}

.title-bar svg {
  width: 18px;
  height: 18px;
  margin-left: 16px;
  margin-right: 12px;
}

.title-bar span {
  font-size: 10pt;
  user-select: none;
}
</style>
