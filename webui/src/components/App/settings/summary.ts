// 结构化配置项在卡片右侧那句摘要
//
// 优先级、字幕语言、弹幕样式这些项的内容藏在各自的对话框里，卡片上光有一个「自定义…」
// 按钮的话，用户每次都得点开才知道现在设的是什么。
//
// 抽成模块而不是留在设置页里：下载选项对话框的「附加内容」页渲染的是**同一批项**
// （弹幕样式、字幕语言、字幕样式），那边同样要这句摘要。留在页面里就得抄第二份，
// 而抄的那份会在加新项时被漏掉 —— 表现是同一张卡片在两处显示得不一样。

import { t, mediaLabel } from '@/i18n'
import type { SettingSpec } from './spec'

/** 只用到 settingsStore 的这两块，写成接口是为了不把这个模块绑死在 store 上 */
interface SummarySource {
  value: (attr: string) => unknown
  choices: { [group: string]: { value: unknown; label: string }[] } | null
}

export function settingSummary(spec: SettingSpec, source: SummarySource): string | undefined {
  if (spec.kind !== 'dialog') {
    return undefined
  }

  const value = source.value(spec.attr)

  if (spec.dialog === 'priority') {
    // 首选的那一档最有信息量 —— 这个列表回答的就是「优先要哪个」
    const first = Array.isArray(value) ? value[0] : undefined

    if (first === undefined) {
      return undefined
    }

    return t('settings.priority.summary', { first: choiceLabel(spec, first, source) })
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

    return count ? t('settings.browseRoots.summary', { count }) : t('settings.browseRoots.summaryEmpty')
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

  if (spec.dialog === 'userAgent') {
    // UA 很长，卡片上放不下。截一段让用户认得出改没改过就够了
    const text = String(value ?? '')

    return text.length > 40 ? `${text.slice(0, 40)}…` : text
  }

  return undefined
}

/**
 * 把一个候选值翻成显示名
 *
 * **标签用前端自己那份翻译**（D12）：后端给的 label 来自 core 的 `Translator`，
 * 而服务端进程里没装 Qt 的翻译函数，拿到的一律是英文。认不出的值才回落到它
 */
function choiceLabel(spec: SettingSpec, value: unknown, source: SummarySource): string {
  const group = spec.choices

  if (!group) {
    return String(value)
  }

  const fallback = source.choices?.[group]?.find((choice) => choice.value === value)?.label

  return mediaLabel(group, value as string | number, fallback ?? String(value))
}
