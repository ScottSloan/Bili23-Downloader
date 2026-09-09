<script setup lang="ts">
/**
 * 标题栏
 *
 * 桌面版这里只有图标与应用名（窗口按钮由系统画）。Web 端右侧多两样，
 * 都是**桌面版没有的**：
 *
 * - **主题快捷切换**。桌面版切主题要进设置页的「个性化」，那边窗口就在眼前、
 *   切一次是低频操作；网页上主题只存在浏览器本地（D14），换设备就得重设一次，
 *   放个一键切换省事得多。设置页那一项仍然保留，两处改的是同一个状态
 * - **有新版本时的提示**。桌面版是启动后自动弹对话框；网页上弹窗打断操作更讨厌，
 *   所以做成标题栏上一个带小圆点的按钮，点了才看详情
 * - **退出会话**。桌面版没有「登录这个程序」这回事，网页有 —— 而且共用电脑上
 *   离开时能退出登录是基本需求。**退的是这个网页的会话，不是 B 站账号**
 */
import { computed, onMounted, ref } from 'vue'
import IconApp from '@/components/Fluent/icons/IconApp.vue'
import transparentToolButton from '@/components/Fluent/components/widgets/button/TransparentToolButton.vue'
import updateDialog from '@/components/App/UpdateDialog.vue'
import logoutDialog from '@/components/App/LogoutDialog.vue'
import { useThemeStore } from '@/stores/themeStore'
import { useUpdateStore } from '@/stores/updateStore'
import { useToastStore } from '@/stores/toastStore'
import { useAuthStore } from '@/stores/authStore'
import { t } from '@/i18n'

const themeStore = useThemeStore()
const updateStore = useUpdateStore()
const toast = useToastStore()
const authStore = useAuthStore()

const updateOpen = ref(false)
const logoutOpen = ref(false)

async function confirmLogout() {
  logoutOpen.value = false

  await authStore.logout()
}

// 浅色 → 深色 → 跟随系统 → 浅色。与设置页那个下拉是同一份状态
const ORDER = ['light', 'dark', 'auto'] as const

const themeIcon = computed(() => {
  switch (themeStore.mode) {
    case 'light':
      return 'brightness'
    case 'dark':
      return 'quietHours'
    default:
      // 跟随系统用「对比度」那个图标，与前两个一眼能分开
      return 'constract'
  }
})

const themeLabel = computed(() => t(`settings.theme.${themeStore.mode === 'auto' ? 'system' : themeStore.mode}`))

function cycleTheme() {
  const next = ORDER[(ORDER.indexOf(themeStore.mode as (typeof ORDER)[number]) + 1) % ORDER.length]

  themeStore.setMode(next)
}

async function checkUpdate() {
  // 已经知道有新版本了就直接看详情，不必再问一次
  if (updateStore.available) {
    updateOpen.value = true

    return
  }

  const result = await updateStore.check(true)

  if (result.error) {
    toast.error(t('update.checkFailed'), result.error)

    return
  }

  if (result.available) {
    updateOpen.value = true

    return
  }

  toast.success(t('toast.done'), t('update.alreadyLatest'))
}

// 进页面查一次。查不到就安静地算了 —— 版本服务连不上不是用户此刻要处理的事
onMounted(() => {
  void updateStore.check()
})
</script>

<template>
  <div class="title-bar">
    <IconApp />
    <span class="app-name">Bili23 Downloader</span>

    <span class="stretch" />

    <div style="display: flex; gap: 8px; padding-right: 16px">
      <!-- 有新版本时才出现。没有的话标题栏上多一个永远没反应的按钮只是噪声 -->
      <div v-if="updateStore.available" class="with-dot">
        <transparentToolButton
          icon="update"
          :label="t('update.available', { version: updateStore.version })"
          @click="checkUpdate"
        />
        <span class="dot"></span>
      </div>

      <transparentToolButton
        :icon="themeIcon"
        :label="t('settings.theme.label') + '：' + themeLabel"
        @click="cycleTheme"
      />

      <transparentToolButton icon="exit" :label="t('user.logout')" @click="logoutOpen = true" />

    </div>

    <updateDialog :open="updateOpen" @close="updateOpen = false" />

    <logoutDialog :open="logoutOpen" @close="logoutOpen = false" @confirm="confirmLogout" />
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

.title-bar > svg {
  width: 18px;
  height: 18px;
  margin-left: 16px;
  margin-right: 12px;
}

.app-name {
  font-size: 13px;
  user-select: none;
}

.stretch {
  flex: 1 1 auto;
}

/* 最右边那个按钮与窗口边缘留 12，与桌面版标题栏右侧的留白一致 */
.title-bar > :deep(button:last-of-type) {
  margin-right: 12px;
}

.with-dot {
  position: relative;
  display: flex;
  margin-right: 4px;
}

/* 小圆点压在图标右上角。加它是因为「有更新」与「没更新」两个状态下图标本身一样，
   光靠有没有这个按钮，用户不会注意到它是新出现的 */
.dot {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  pointer-events: none;
  background-color: var(--primary-color);
  /* 描一圈底色，压在图标线条上时才分得清 */
  box-shadow: 0 0 0 2px var(--solid-bg-base);
}
</style>
