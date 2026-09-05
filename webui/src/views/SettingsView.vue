<script setup lang="ts">
import fluentLabel from '@/components/Fluent/components/widgets/label/FluentLabel.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import { useThemeStore } from '@/stores/themeStore'
import { t } from '@/i18n'

const themeStore = useThemeStore()
</script>

<template>
  <div class="page-view">
    <fluentLabel :text="t('settings.theme.label')" />

    <div class="actions">
      <!-- 三档与 GUI 的主题设置一致（Light / Dark / System default），当前档位记在 themeStore.mode -->
      <pushButton :title="t('settings.theme.light')" @click="themeStore.setMode('light')" />
      <pushButton :title="t('settings.theme.dark')" @click="themeStore.setMode('dark')" />
      <pushButton :title="t('settings.theme.system')" @click="themeStore.setMode('auto')" />
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
