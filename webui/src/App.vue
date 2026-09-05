<script setup lang="ts">
import { onMounted } from 'vue'
import MainWindow from '@/MainWindow.vue'
import { useThemeStore } from '@/stores/themeStore'
import { api } from '@/api/client'
import { setLocale } from '@/i18n'

const themeStore = useThemeStore()

// 主题在 index.html 的首屏脚本里已经写过一次，这里补齐主题色色阶并开始监听系统主题
themeStore.initialize()

// 界面语言跟随桌面版的设置（两边共用 config.json）。取不到就保持按浏览器语言渲染
onMounted(async () => {
  try {
    setLocale((await api.getStatus()).language)
  } catch {
    // 后端没起来不该拦住界面渲染
  }
})
</script>

<template>
  <MainWindow />
</template>

<style>
.flex-stretch {
  flex-grow: 1;
}

.rounded {
  border-radius: 8px;
}
</style>
