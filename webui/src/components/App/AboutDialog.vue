<script setup lang="ts">
/**
 * 关于
 *
 * 对应桌面版 `gui/dialog/main_window/about.py`。**在 GUI 里它也不是一个页面**，
 * 而是导航栏上一个 `selectable = False` 的项，点了弹这个对话框 —— 这边照做。
 *
 * 版本号来自 `/api/status`（appStore 启动时已经取过），不在前端写死：
 * 写死的那份升级时没人会想起来改，而且不报错，只是一直显示旧版本。
 *
 * 桌面版那一行印的是 Qt 与 QFluentWidgets 的版本。这里换成 Vue ——
 * **WebUI 这个进程里根本没有 Qt**（D16），照抄过来是句假话。
 */
import { computed, ref } from 'vue'
import { version as vueVersion } from 'vue'
import { useAppStore } from '@/stores/appStore'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import transparentToolButton from '@/components/Fluent/components/widgets/button/TransparentToolButton.vue'
import termsDialog from './TermsDialog.vue'
import { t } from '@/i18n'

const APP_NAME = 'Bili23 Downloader'

const DOCUMENTATION_URL = 'https://bili23.scott-sloan.cn/doc/introduction.html'
const GITHUB_URL = 'https://github.com/ScottSloan/Bili23-Downloader'
const SPONSOR_URL = 'https://bili23.scott-sloan.cn/doc/about.html'

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const appStore = useAppStore()

const termsOpen = ref(false)

/** 拿不到版本号时留空，不要显示 "版本 undefined" */
const version = computed(() => appStore.version || '—')

const year = new Date().getFullYear()

function openLink(url: string) {
  // noopener：新开的页面拿不到 window.opener，免得它能反过来改这边的地址
  window.open(url, '_blank', 'noopener')
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('about.title', { app: APP_NAME })"
    width="600px"
    @close="emit('close')"
  >
    <div class="about">
      <p class="line">{{ t('about.version', { version }) }}</p>
      <p class="line">{{ t('about.stack', { vue: vueVersion }) }}</p>

      <p class="block">{{ t('about.license') }}</p>
      <p class="block">{{ t('about.copyright', { year }) }}</p>

      <p class="sponsor">{{ t('about.sponsor') }}</p>

      <!-- 四个按钮居中一排，与桌面版那个 addStretch 夹着的 button_layout 一致 -->
      <div class="links">
        <transparentToolButton
          icon="document"
          :label="t('about.terms')"
          :text="t('about.terms')"
          @click="termsOpen = true"
        />
        <transparentToolButton
          icon="help"
          :label="t('about.documentation')"
          :text="t('about.documentation')"
          @click="openLink(DOCUMENTATION_URL)"
        />
        <transparentToolButton
          icon="github"
          label="Github"
          text="Github"
          @click="openLink(GITHUB_URL)"
        />
        <transparentToolButton
          icon="heart"
          :label="t('about.sponsorAction')"
          :text="t('about.sponsorAction')"
          @click="openLink(SPONSOR_URL)"
        />
      </div>
    </div>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.ok')" @click="emit('close')" />
    </template>
  </fluentDialog>

  <!-- 条款叠在关于之上。它自己也是一个 fluentDialog，遮罩会盖住底下那层 -->
  <termsDialog :open="termsOpen" @close="termsOpen = false" />
</template>

<style scoped>
.about {
  display: flex;
  flex-direction: column;
}

/* 版本那两行贴在一起（桌面版是 setSpacing(0) 的 content_layout） */
.line {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
}

/* 许可证与版权各自前面空一档，对应桌面版的 addSpacing(10) */
.block {
  margin: 10px 0 0 0;
  font-size: 14px;
  color: var(--text-primary);
}

/* 赞助那段前面空得多一些（addSpacing(30)），它是另一个话题 */
.sponsor {
  margin: 30px 0 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.links {
  display: flex;
  flex-direction: row;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
  flex-wrap: wrap;
}
</style>
