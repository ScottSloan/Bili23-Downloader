<script setup lang="ts">
import titleBar from '@/components/App/TitleBar.vue'
import navigationBar from '@/components/Fluent/components/navigation/NavigationBar.vue'
import navigationPanel from './components/Fluent/components/navigation/NavigationPanel.vue'
import navigationBarButton from './components/Fluent/components/navigation/NavigationBarButton.vue'
import navigationBarStretch from '@/components/Fluent/components/navigation/NavigationBarStretch.vue'
import navigationBarAvatar from '@/components/Fluent/components/navigation/NavigationBarAvatar.vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { t } from '@/i18n'
import { IconDownload, IconSearch, IconSettings } from '@/components/Fluent/icons'

const route = useRoute()

const activeNavIndex = computed(() => {
  const map: Record<string, number> = {
    '/parse': 0,
    '/download': 1,
    '/settings': 2,
  }

  return map[route.path] ?? 0
})
</script>

<template>
  <div class="main-interface">
    <titleBar />
    <div class="main-content">
      <navigationBar :active-index="activeNavIndex">
        <navigationBarButton :title="t('nav.parse')" :icon="IconSearch" to="/parse" />
        <navigationBarButton :title="t('nav.download')" :icon="IconDownload" to="/download" />
        <navigationBarStretch />
        <!-- 头像在设置项之上，与 GUI 的导航栏顺序一致 -->
        <navigationBarAvatar />
        <navigationBarButton :title="t('nav.settings')" :icon="IconSettings" to="/settings" />
      </navigationBar>
      <navigationPanel>
        <router-view v-slot="{ Component }">
          <transition name="pop-up" mode="out-in">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </navigationPanel>
    </div>
  </div>
</template>

<style scoped>
.main-interface {
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  transition: background-color 0.2s ease;
  background-color: var(--solid-bg-base);
  display: flex;
  flex-direction: column;
}

.main-content {
  display: flex;
  flex-direction: row;
  flex: 1 1 auto;
  min-height: 0;
}

.pop-up-enter-active {
  transition:
    transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94),
    opacity 0.25s ease-out;
}

.pop-up-enter-from {
  transform: translateY(76px);
  opacity: 0;
}

.pop-up-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}
</style>
