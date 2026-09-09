<script setup lang="ts">
import titleBar from '@/components/App/TitleBar.vue'
import infoBarHost from '@/components/Fluent/components/info_bar/InfoBarHost.vue'
import navigationBar from '@/components/Fluent/components/navigation/NavigationBar.vue'
import navigationPanel from './components/Fluent/components/navigation/NavigationPanel.vue'
import navigationBarButton from './components/Fluent/components/navigation/NavigationBarButton.vue'
import navigationBarStretch from '@/components/Fluent/components/navigation/NavigationBarStretch.vue'
import navigationBarAvatar from '@/components/Fluent/components/navigation/NavigationBarAvatar.vue'
import aboutDialog from '@/components/App/AboutDialog.vue'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskStore } from '@/stores/taskStore'
import { t } from '@/i18n'
import { IconDownload, IconSearch, IconSettings } from '@/components/Fluent/icons'

const route = useRoute()
const taskStore = useTaskStore()

const aboutOpen = ref(false)

/**
 * 高亮条落在第几个按钮上
 *
 * **数的是 `.navigation-bar-button` 的顺序，不是路由的个数**：中间那个「关于」
 * 不指向任何一页，但它同样是一个按钮，占掉一位。漏算它的话，指示条会停在
 * 「关于」上而当前其实在设置页 —— 不报错，只是指错了
 */
const activeNavIndex = computed(() => {
  const map: Record<string, number> = {
    '/parse': 0,
    '/download': 1,
    // 2 是「关于」，它没有对应的路由
    '/settings': 3,
  }

  return map[route.path] ?? 0
})
</script>

<template>
  <div class="main-interface">
    <!-- 气泡提示挂在最外层：它 teleport 到 body，切页不该把正在显示的提示带走 -->
    <infoBarHost />

    <titleBar />
    <div class="main-content">
      <navigationBar :active-index="activeNavIndex">
        <navigationBarButton :title="t('nav.parse')" :icon="IconSearch" to="/parse" />
        <navigationBarButton
          :title="t('nav.download')"
          :icon="IconDownload"
          to="/download"
          :badge="taskStore.pendingCount"
        />
        <!--
          「关于」不是一页，是个弹对话框的项 —— 桌面版那边同样是
          `selectable = False` 加一个 onClick，见 main_window.py 的 about_btn。
          位置也照它：在下载与收藏之后、顶部这一组的末尾
        -->
        <navigationBarButton :title="t('nav.about')" icon="info" @click="aboutOpen = true" />

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

    <aboutDialog :open="aboutOpen" @close="aboutOpen = false" />
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
