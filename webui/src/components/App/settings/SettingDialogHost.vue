<script setup lang="ts">
/**
 * 结构化配置项的专用编辑器，集中在这里挂一次
 *
 * 优先级、字幕语言、弹幕 / 字幕样式这些项是列表或字典，一行卡片放不下，各自要一个对话框。
 * 用到它们的地方不止一处：设置页，以及下载选项对话框的「附加内容」页 —— 那两处展示的
 * 本来就是**同一批配置项**（桌面版也是直接复用同一批 SettingCard）。
 *
 * 把接线抄成两份的话，加一个新的结构化项时只在其中一处接上，另一处点「自定义…」
 * 什么都不会发生，而且不报错。所以收敛到这一个组件里。
 *
 * 值与保存都走 `settingsStore`，与那两处页面用的是同一份状态
 */
import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settingsStore'
import { t, mediaLabel } from '@/i18n'
import { SPEC_BY_ATTR, type SettingSpec } from './spec'
import priorityDialog from './PriorityDialog.vue'
import subtitleLanguageDialog from './SubtitleLanguageDialog.vue'
import pathListDialog from './PathListDialog.vue'
import styleDialog from './StyleDialog.vue'
import namingRuleDialog from './NamingRuleDialog.vue'
import userAgentDialog from './UserAgentDialog.vue'
import passwordDialog from './PasswordDialog.vue'
import type { NamingRule } from './NamingRuleDialog.vue'

const props = defineProps<{
  /** 当前打开的是哪一项的编辑器。null 表示一个都没开 */
  attr: string | null
}>()

const emit = defineEmits<{
  close: []
  /** 保存之后。attr 一并给出，调用方据此做后续动作（比如重查一次媒体信息） */
  saved: [attr: string, value: unknown]
}>()

const store = useSettingsStore()

const spec = computed<SettingSpec | null>(() =>
  props.attr ? (SPEC_BY_ATTR[props.attr] ?? null) : null,
)

function save(value: unknown) {
  const attr = props.attr

  if (!attr) {
    return
  }

  store.set(attr, value as never, Boolean(SPEC_BY_ATTR[attr]?.restart))

  emit('saved', attr, value)
  emit('close')
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
const choices = computed<{ value: string | number; label: string }[]>(() => {
  const group = spec.value?.choices

  if (!group || !store.choices) {
    return []
  }

  return (store.choices[group] ?? []).map((choice) => ({
    value: choice.value as string | number,
    label: mediaLabel(group, choice.value as string | number, choice.label),
  }))
})

/** 字幕对齐：标签后面跟上 ASS 的编号，与桌面版一致（光看数字认不出是哪个角） */
const alignmentOptions = computed(() =>
  (store.choices?.subtitle_alignment ?? []).map((entry) => ({
    value: entry.value as string | number,
    label: `${mediaLabel('subtitle_alignment', entry.value as string | number, entry.label)} (${entry.value})`,
  })),
)
</script>

<template>
  <priorityDialog
    :open="spec?.dialog === 'priority'"
    :title="attr ? t(`settings.label.${attr}`) : ''"
    :choices="choices"
    :value="(store.value(attr ?? '') as (number | string)[]) ?? []"
    @close="emit('close')"
    @save="save"
  />

  <subtitleLanguageDialog
    :open="spec?.dialog === 'subtitleLanguage'"
    :choices="choices"
    :value="(store.value('subtitle_language') as Record<string, never>) ?? null"
    @close="emit('close')"
    @save="save"
  />

  <pathListDialog
    :open="spec?.dialog === 'browseRoots'"
    :value="(store.value('webui_browse_roots') as string[]) ?? []"
    @close="emit('close')"
    @save="save"
  />

  <styleDialog
    :open="spec?.dialog === 'danmakuStyle' || spec?.dialog === 'subtitleStyle'"
    :kind="spec?.dialog === 'subtitleStyle' ? 'subtitle' : 'danmaku'"
    :value="(store.value(attr ?? '') as Record<string, unknown>) ?? null"
    :fonts="store.fonts"
    :alignments="alignmentOptions"
    @close="emit('close')"
    @save="save"
  />

  <namingRuleDialog
    :open="spec?.dialog === 'namingRule'"
    :value="(store.value('naming_rule_list') as NamingRule[]) ?? []"
    @close="emit('close')"
    @save="save"
  />

  <userAgentDialog
    :open="spec?.dialog === 'userAgent'"
    :value="String(store.value('user_agent') ?? '')"
    :default-value="String(store.item('user_agent')?.default ?? '')"
    @close="emit('close')"
    @save="save"
  />

  <!-- 改口令不经过 store：那一项在 /api/settings 里根本不存在，
       对话框自己去调 /api/auth/password，所以没有 @save -->
  <passwordDialog :open="spec?.dialog === 'password'" @close="emit('close')" />
</template>
