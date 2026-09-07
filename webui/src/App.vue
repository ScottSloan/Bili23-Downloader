<script setup lang="ts">
import { onMounted, watch } from 'vue'
import MainWindow from '@/MainWindow.vue'
import LoginView from '@/views/LoginView.vue'
import { useThemeStore } from '@/stores/themeStore'
import { useAppStore } from '@/stores/appStore'
import { useAuthStore } from '@/stores/authStore'
import { useTaskStore } from '@/stores/taskStore'
import { setUnauthorizedHandler } from '@/api'

const themeStore = useThemeStore()
const appStore = useAppStore()
const authStore = useAuthStore()
const taskStore = useTaskStore()

// 主题在 index.html 的首屏脚本里已经写过一次，这里补齐主题色色阶并开始监听系统主题
themeStore.initialize()

// 会话过期可能发生在任何一次请求上。统一在这里接管，比让每个调用点各写一遍
// 「捕获 401 → 跳登录」可靠得多 —— 后者一定会漏掉几处
// 只改状态，不动路由：登录页由下面的模板接管，路由停在原处 ——
// 重新登录后用户回到的正是他刚才那一页，不必绕一圈 redirect 参数
setUnauthorizedHandler(() => authStore.onSessionExpired())

// 登录之后再去拉版本、账号、语言：未登录时这些请求只会得到 401
//
// 任务流也在这里起停，**不再跟着下载页的进出**。导航栏上的下载数角标要求它一直是新的，
// 而用户多数时间待在解析页 —— 跟着页面起停的话，角标只在你正看着下载页时才准，
// 那正是最不需要它的时候
watch(
  () => authStore.authenticated,
  (authenticated) => {
    if (authenticated) {
      appStore.fetchStatus()
      taskStore.start()
    } else {
      taskStore.stop()
    }
  },
  { immediate: true },
)

onMounted(() => {
  if (authStore.checking) {
    authStore.check()
  }
})
</script>

<template>
  <!--
    会话还没查出来时先什么都不显示：直接渲染主界面会闪一下再跳登录页，
    直接渲染登录页则会在已登录的情况下白闪一次表单
  -->
  <div v-if="authStore.checking" class="booting" />
  <LoginView v-else-if="!authStore.authenticated" />
  <MainWindow v-else />
</template>

<style>
.flex-stretch {
  flex-grow: 1;
}

.rounded {
  border-radius: 8px;
}

.booting {
  width: 100%;
  height: 100%;
  background-color: var(--solid-bg-base);
}
</style>
