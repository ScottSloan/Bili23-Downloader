<script setup lang="ts">
import { onMounted } from 'vue'
import MainWindow from '@/MainWindow.vue'
import { useThemeStore } from '@/stores/themeStore'
import { useAppStore } from '@/stores/appStore'

const themeStore = useThemeStore()
const appStore = useAppStore()

// 主题在 index.html 的首屏脚本里已经写过一次，这里补齐主题色色阶并开始监听系统主题
themeStore.initialize()

// 版本、登录态、界面语言一次拉齐。取不到不拦渲染，界面按未登录 + 浏览器语言显示
onMounted(() => appStore.fetchStatus())
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
