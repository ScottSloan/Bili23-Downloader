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
import { t, setLocale, mediaLabel } from '@/i18n'
import {
  SETTING_GROUPS,
  INTERFACE_ITEMS,
  SPEC_BY_ATTR,
  isExpandCard,
  type SettingSpec,
} from '@/components/App/settings/spec'
import settingRow from '@/components/App/settings/SettingRow.vue'
import priorityDialog from '@/components/App/settings/PriorityDialog.vue'
import subtitleLanguageDialog from '@/components/App/settings/SubtitleLanguageDialog.vue'
import pathListDialog from '@/components/App/settings/PathListDialog.vue'
import styleDialog from '@/components/App/settings/StyleDialog.vue'
import namingRuleDialog from '@/components/App/settings/NamingRuleDialog.vue'
import type { NamingRule } from '@/components/App/settings/NamingRuleDialog.vue'
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

const openSpec = computed<SettingSpec | null>(() =>
  openAttr.value ? (SPEC_BY_ATTR[openAttr.value] ?? null) : null,
)

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

function save(value: unknown) {
  if (openAttr.value) {
    store.set(openAttr.value, value as never, Boolean(SPEC_BY_ATTR[openAttr.value]?.restart))
  }

  openAttr.value = null
}

/**
 * 对话框要用的候选表
 *
 * 两件事：
 *
 * 1. 后端那边 `Choice.value` 是 `Any`（画质是整数、字幕语言是字符串代码），生成的类型
 *    因此是 `unknown`。**收窄放在这一处**，而不是让每个对话框都去处理 unknown
 * 2. **标签用前端自己那份翻译**（D12）。后端给的 label 只当兜底 —— 服务端没装 Qt 的
 *    翻译函数，它给出来的一律是英文
 *
 * 字幕语言是例外：那 158 条是 B 站自己的语言表，源数据只有中文名，前端没有第二份
 * 可抄，所以直接用后端给的（`mediaLabel` 认不出就回落到它）
 */
function choicesOf(spec: SettingSpec | null): { value: string | number; label: string }[] {
  if (!spec?.choices || !store.choices) {
    return []
  }

  return (store.choices[spec.choices] ?? []).map((choice) => ({
    value: choice.value as string | number,
    label: mediaLabel(spec.choices as string, choice.value as string | number, choice.label),
  }))
}

/** 字幕对齐：标签后面跟上 ASS 的编号，与桌面版一致（光看数字认不出是哪个角） */
const alignmentOptions = computed(() =>
  (store.choices?.subtitle_alignment ?? []).map((entry) => ({
    value: entry.value as string | number,
    label: `${mediaLabel('subtitle_alignment', entry.value as string | number, entry.label)} (${entry.value})`,
  })),
)

/**
 * 卡片右侧那句摘要
 *
 * 结构化项在卡片上看不到内容，不给一句摘要的话，用户每次都得点开才知道现在设的是什么
 */
function summaryOf(spec: SettingSpec): string | undefined {
  if (spec.kind !== 'dialog') {
    return undefined
  }

  const value = store.value(spec.attr)

  if (spec.dialog === 'priority') {
    // 首选的那一档最有信息量 —— 这个列表回答的就是「优先要哪个」
    const first = Array.isArray(value) ? value[0] : undefined

    if (first === undefined) {
      return undefined
    }

    const label = choicesOf(spec).find((choice) => choice.value === first)?.label

    return t('settings.priority.summary', { first: label ?? String(first) })
  }

  if (spec.dialog === 'subtitleLanguage') {
    const detail = (value ?? {}) as { download_specified?: boolean; specified_language?: string[] }

    return detail.download_specified
      ? t('settings.subtitleLanguage.summarySome', {
          count: detail.specified_language?.length ?? 0,
        })
      : t('settings.subtitleLanguage.summaryAll')
  }

  if (spec.dialog === 'browseRoots') {
    const count = Array.isArray(value) ? value.length : 0

    return count
      ? t('settings.browseRoots.summary', { count })
      : t('settings.browseRoots.summaryEmpty')
  }

  if (spec.dialog === 'danmakuStyle' || spec.dialog === 'subtitleStyle') {
    // 字体名 + 字号最能说明当前设的是什么
    const font = (value as { font?: { name?: string; size?: number } } | null)?.font

    return font?.name ? `${font.name} · ${font.size ?? ''}` : undefined
  }

  if (spec.dialog === 'namingRule') {
    const count = Array.isArray(value) ? value.length : 0

    return t('settings.namingRule.summary', { count })
  }

  return undefined
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
          :description="`${t('settings.theme.description')}（${t('settings.localOnly')}）`"
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
          :description="`${t('settings.accent.description')}（${t('settings.localOnly')}）`"
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

    <priorityDialog
      :open="openSpec?.dialog === 'priority'"
      :title="openAttr ? t(`settings.label.${openAttr}`) : ''"
      :choices="choicesOf(openSpec)"
      :value="(store.value(openAttr ?? '') as (number | string)[]) ?? []"
      @close="openAttr = null"
      @save="save"
    />

    <subtitleLanguageDialog
      :open="openSpec?.dialog === 'subtitleLanguage'"
      :choices="choicesOf(openSpec)"
      :value="(store.value('subtitle_language') as Record<string, never>) ?? null"
      @close="openAttr = null"
      @save="save"
    />

    <pathListDialog
      :open="openSpec?.dialog === 'browseRoots'"
      :value="(store.value('webui_browse_roots') as string[]) ?? []"
      @close="openAttr = null"
      @save="save"
    />

    <styleDialog
      :open="openSpec?.dialog === 'danmakuStyle' || openSpec?.dialog === 'subtitleStyle'"
      :kind="openSpec?.dialog === 'subtitleStyle' ? 'subtitle' : 'danmaku'"
      :value="(store.value(openAttr ?? '') as Record<string, unknown>) ?? null"
      :fonts="store.fonts"
      :alignments="alignmentOptions"
      @close="openAttr = null"
      @save="save"
    />

    <namingRuleDialog
      :open="openSpec?.dialog === 'namingRule'"
      :value="(store.value('naming_rule_list') as NamingRule[]) ?? []"
      @close="openAttr = null"
      @save="save"
    />
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
