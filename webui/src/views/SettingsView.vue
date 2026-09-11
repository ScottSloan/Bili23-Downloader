<script setup lang="ts">
// 设置页
//
// 分两类：
//
// - **主题与强调色**只存在浏览器本地（D14：两端各存各的）。同一份 config.json 是
//   GUI 与 WebUI 共用的，主题跟着走的话，在手机上切一次深色会把桌面版也切了
// - **其余项**读写 `/api/settings`，与桌面版共用同一份配置
//
// 保存是自动的：改完就存，攒 400ms 合并成一次请求（见 settingsStore）。
// 没有「保存」按钮 —— 桌面版也没有，两边行为保持一致。
//
// 结构化的项（优先级、字幕语言、可浏览目录）各有一个对话框，**统一在这里托管**：
// 放进 SettingRow 的话，每一行都会带着一个自己永远用不到的对话框。

import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useSettingsStore } from '@/stores/settingsStore'
import { useThemeStore } from '@/stores/themeStore'
import { useToastStore } from '@/stores/toastStore'
import { t, setLocale } from '@/i18n'
import {
  SETTING_GROUPS,
  INTERFACE_ITEMS,
  isExpandCard,
  type SettingSpec,
} from '@/components/App/settings/spec'
import settingRow from '@/components/App/settings/SettingRow.vue'
import settingDialogHost from '@/components/App/settings/SettingDialogHost.vue'
import { settingSummary } from '@/components/App/settings/summary'
import settingCardGroup from '@/components/Fluent/components/settings/SettingCardGroup.vue'
import expandSettingCard from '@/components/Fluent/components/settings/ExpandSettingCard.vue'
import settingGroupRow from '@/components/Fluent/components/settings/SettingGroupRow.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'

const store = useSettingsStore()
const themeStore = useThemeStore()
const toast = useToastStore()

// 保存失败弹气泡。设置页是「改完就存」的，失败要是只在页面上留一行小字，
// 用户多半已经滚到别处去了
watch(
  () => store.error,
  (message) => {
    if (message) {
      toast.error(t('toast.saveFailed'), message)
    }
  },
)

/** 当前打开的是哪一项的对话框。null 表示没开 */
const openAttr = ref<string | null>(null)

const themeOptions = computed(() => [
  { value: 'light', label: t('settings.theme.light') },
  { value: 'dark', label: t('settings.theme.dark') },
  { value: 'auto', label: t('settings.theme.system') },
])

const restartNotice = computed(() =>
  store.pendingRestart.length
    ? t('settings.restartNotice', {
        items: store.pendingRestart.map((attr) => t(`settings.label.${attr}`)).join('、'),
      })
    : '',
)

onMounted(() => {
  void store.load()

  // 候选表也一起拉：卡片上的摘要要靠它把 id 翻成画质名（7.5 KB，不值得为它做懒加载）
  void store.loadChoices()
})

// 离开设置页时把攒着的改动立刻发出去。少了这一步，改完最后一项就切页的话，
// 那 400ms 的合并窗口还没到，改动会跟着组件一起消失
onUnmounted(() => {
  void store.flush()
})

/** 语言要立刻反映到界面上，不能等下次刷新 */
function onChanged(attr: string, value: unknown) {
  if (attr === 'language') {
    setLocale(typeof value === 'string' ? value : null)
  }
}

async function onOpenDialog(attr: string) {
  // 进页面时已经拉过了，这里兜住「那次失败了」的情况。store 自己去重
  await store.loadChoices()

  openAttr.value = attr
}

/** 编辑器存完之后的收尾。目前只有关掉自己，留着钩子是因为宿主已经把 attr 带回来了 */
function onSaved(_attr: string, _value: unknown) {
  openAttr.value = null
}

/** 卡片右侧那句摘要。实现在 settings/summary.ts，与下载选项对话框共用一份 */
function summaryOf(spec: SettingSpec): string | undefined {
  return settingSummary(spec, store)
}

</script>

<template>
  <div class="page-view">
    <p v-if="store.loading && !store.loaded" class="status">{{ t('settings.loading') }}</p>

    <p v-if="restartNotice" class="status notice">{{ restartNotice }}</p>

    <settingCardGroup :title="t('settings.group.interface')">
      <!--
        对应桌面版的 PersonalizationCard。主题与主题色不走 /api/settings（D14 两端各存各的），
        所以这两行手写，不经过 SettingRow
      -->
      <expandSettingCard
        icon="palette"
        :title="t('settings.card.personalization.title')"
        :description="t('settings.card.personalization.desc')"
      >
        <settingGroupRow
          :title="t('settings.theme.label')"
          :description="t('settings.theme.description')"
        >
          <comboBox
            :model-value="themeStore.mode"
            :options="themeOptions"
            :label="t('settings.theme.label')"
            @update:model-value="(value) => themeStore.setMode(String(value))"
          />
        </settingGroupRow>

        <settingGroupRow
          :title="t('settings.accent.label')"
          :description="t('settings.accent.description')"
        >
          <!-- 原生取色器：各平台自带的那个，比自己搭一个色轮可靠得多 -->
          <input
            type="color"
            class="color-input"
            :value="themeStore.primaryColor"
            :aria-label="t('settings.accent.label')"
            @input="themeStore.setPrimaryColor(($event.target as HTMLInputElement).value)"
          />
          <pushButton :title="t('settings.accent.reset')" @click="themeStore.setPrimaryColor('')" />
        </settingGroupRow>
      </expandSettingCard>

      <settingRow
        v-for="spec in INTERFACE_ITEMS"
        :key="spec.attr"
        :spec="spec"
        :summary="summaryOf(spec)"
        @changed="onChanged"
        @open-dialog="onOpenDialog"
      />
    </settingCardGroup>

    <settingCardGroup
      v-for="group in SETTING_GROUPS"
      :key="group.key"
      :title="t(`settings.group.${group.key}`)"
    >
      <template v-for="entry in group.items">
        <expandSettingCard
          v-if="isExpandCard(entry)"
          :key="entry.key"
          :icon="entry.icon"
          :title="t(`settings.card.${entry.key}.title`)"
          :description="t(`settings.card.${entry.key}.desc`)"
        >
          <settingRow
            v-for="spec in entry.items"
            :key="spec.attr"
            :spec="spec"
            :summary="summaryOf(spec)"
            in-group
            @changed="onChanged"
            @open-dialog="onOpenDialog"
          />
        </expandSettingCard>

        <settingRow
          v-else
          :key="entry.attr"
          :spec="entry"
          :summary="summaryOf(entry)"
          @changed="onChanged"
          @open-dialog="onOpenDialog"
        />
      </template>
    </settingCardGroup>

    <!--
      结构化项的编辑器统一挂在这里。**不要放进 SettingRow** ——
      那样每一行都会带着一堆自己永远用不到的对话框。

      接线本身在 SettingDialogHost 里，下载选项对话框的「附加内容」页用的是同一个
    -->
    <settingDialogHost :attr="openAttr" @close="openAttr = null" @saved="onSaved" />
  </div>
</template>

<style scoped>
/* 页面边距与组间距抄自桌面版 setting.py：contentsMargins(30, 10, 30, 0) + setSpacing(28)，
   底部那 20 是它最后 addSpacing(20) 留的 */
.page-view {
  height: 100%;
  overflow-y: auto;
  padding: 10px 30px 20px 30px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.status {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.status.error {
  color: var(--text-danger);
}

.status.notice {
  padding: 8px 12px;
  border-radius: 6px;
  color: var(--text-primary);
  background-color: var(--control-fill-secondary);
  border: 1px solid var(--card-stroke-default);
}

.color-input {
  width: 42px;
  height: 30px;
  padding: 2px;
  border-radius: 5px;
  cursor: pointer;
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
}
</style>
