<script setup lang="ts">
import { useAppStore } from '@/stores/appStore'
import { t } from '@/i18n'

const appStore = useAppStore()
</script>

<template>
  <!--
    位置与尺寸对齐 GUI：导航栏底部、设置项之上，64×64 的槽位里放一个直径 38 的圆形头像，
    不显示用户名（GUI 的 NavigationLargeAvatarWidget 传的 name 就是空串）。

    目前是纯展示。GUI 里点头像会打开登录对话框，Web 端的登录流程在 S4-4，届时这里接上
  -->
  <div
    class="navigation-bar-avatar"
    :title="appStore.loggedIn ? appStore.uname : t('user.signedOut')"
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
  </div>
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
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--control-stroke-default);
}

.avatar-placeholder {
  background-color: var(--control-fill-default);
}
</style>
