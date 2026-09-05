<script setup>
import fluentLabel from '@/components/Fluent/components/widgets/label/FluentLabel.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()
</script>

<template>
  <div class="page-view">
    <fluentLabel text="设置页面" />
    <div class="actions">
      <pushButton title="Light Mode" @click="themeStore.setTheme('light')" />
      <pushButton title="Dark Mode" @click="themeStore.setTheme('dark')" />
      <pushButton title="Toggle Theme" @click="themeStore.toggleTheme" />
    </div>
  </div>
</template>

<style scoped>
.page-view {
  padding: 15px 25px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
