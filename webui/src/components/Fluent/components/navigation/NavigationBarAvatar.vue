<script setup lang="ts">
/**
 * 导航栏底部的头像
 *
 * 与桌面版 `on_avatar_click` 同一套分支：**未登录点它弹登录对话框，已登录点它弹用户卡片**。
 * 位置与尺寸也照 GUI：导航栏底部、设置项之上，64×64 的槽位里放一个直径 38 的圆形头像，
 * 不显示用户名（`NavigationLargeAvatarWidget` 传的 name 就是空串）。
 */
import { ref } from 'vue'
import { useAppStore } from '@/stores/appStore'
import bilibiliLoginDialog from '@/components/App/login/BilibiliLoginDialog.vue'
import profileCard from '@/components/App/login/ProfileCard.vue'
import { t } from '@/i18n'

const appStore = useAppStore()

const root = ref<HTMLElement | null>(null)
const loginOpen = ref(false)
const profileOpen = ref(false)

function onClick() {
  if (appStore.loggedIn) {
    profileOpen.value = !profileOpen.value

    return
  }

  loginOpen.value = true
}
</script>

<template>
  <!--
    原来是个 div，只当展示用。改成 <button>：Tab 走得到、回车能触发，
    读屏软件也知道它是可以点的
  -->
  <button
    ref="root"
    type="button"
    class="navigation-bar-avatar"
    :title="appStore.loggedIn ? appStore.uname : t('login.entry')"
    :aria-label="appStore.loggedIn ? appStore.uname : t('login.entry')"
    @click="onClick"
  >
    <img
      v-if="appStore.loggedIn && appStore.faceUrl"
      class="avatar"
      :src="appStore.faceUrl"
      :alt="t('user.avatarAlt')"
      referrerpolicy="no-referrer"
      draggable="false"
    />
    <!-- 未登录时的占位。GUI 用的是 noface.jpg，Web 端不必为此多带一张图 -->
    <span v-else class="avatar avatar-placeholder" aria-hidden="true"></span>
  </button>

  <bilibiliLoginDialog :open="loginOpen" @close="loginOpen = false" />

  <profileCard v-if="profileOpen" :anchor="root" @close="profileOpen = false" />
</template>

<style scoped>
.navigation-bar-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  flex: 0 0 auto;
  margin-bottom: 5px;
  user-select: none;

  font: inherit;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--control-stroke-default);
  transition: border-color 0.1s ease;
}

.navigation-bar-avatar:hover .avatar {
  border-color: var(--primary-color);
}

.navigation-bar-avatar:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: -4px;
  border-radius: 8px;
}

.avatar-placeholder {
  background-color: var(--control-fill-default);
}
</style>
