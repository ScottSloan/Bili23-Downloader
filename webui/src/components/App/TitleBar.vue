<script setup lang="ts">
import IconApp from '@/components/Fluent/icons/IconApp.vue'
import { useAppStore } from '@/stores/appStore'
import { t } from '@/i18n'

const appStore = useAppStore()
</script>

<template>
  <div class="title-bar">
    <IconApp />
    <span class="app-name">Bili23 Downloader</span>

    <!--
      登录区放在标题栏右侧，而不是像 GUI 那样放左侧导航栏。
      浏览器里这条 48px 本来只是模仿桌面标题栏、不承载任何功能，正好用来放它；
      导航栏则留给纯粹的页面切换
    -->
    <div class="user-area">
      <img
        v-if="appStore.loggedIn && appStore.faceUrl"
        class="avatar"
        :src="appStore.faceUrl"
        :alt="t('titleBar.avatarAlt')"
        referrerpolicy="no-referrer"
        draggable="false"
      />
      <span v-else class="avatar avatar-placeholder" aria-hidden="true"></span>

      <span class="user-name">{{
        appStore.loggedIn ? appStore.uname : t('titleBar.signedOut')
      }}</span>
    </div>
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

.app-name {
  font-size: 10pt;
  user-select: none;
}

.user-area {
  margin-left: auto;
  margin-right: 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  user-select: none;
}

.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex: 0 0 auto;
  object-fit: cover;
  border: 1px solid var(--control-stroke-default);
}

.avatar-placeholder {
  background-color: var(--control-fill-default);
}

.user-name {
  font-size: 10pt;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 未登录时用次级文字色，避免占位文案抢注意力 */
.title-bar:has(.avatar-placeholder) .user-name {
  color: var(--text-secondary);
}
</style>
