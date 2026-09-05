// 前端自建的 i18n
//
// 与 GUI 一致的部分：**英文是源语言**，其余语言由译文覆盖，缺失的键回落到英文；
// 支持的语言与 GUI 相同（en_US / zh_CN / zh_TW + 跟随系统）。
//
// 与 GUI 不同的部分：不共用翻译表。GUI 走 QCoreApplication.translate + .ts / .qm，
// 那属于桌面端，不该跟着 WebUI 进服务端（D12）。共有的串照抄 GUI 的措辞即可，
// 译文可以直接从 src/res/i18n/bili23.*.ts 里取。
//
// 键用的是语义化路径（'parse.submit'）而不是 Qt 那样拿英文源串当键：
// 源串当键在「同一个词不同语境」时会撞车（Qt 靠 context 参数化解），
// 语义化路径没这个问题，代价是与 .ts 对照时要人工找对应。
//
// 实现保持在最小规模，调用形态 t('a.b', { name }) 与 vue-i18n 一致，
// 将来真要换库，调用方不用改。

import { reactive } from 'vue'
import en from './en'
import zhCN from './zh-CN'
import zhTW from './zh-TW'

/** 以英文文件的结构为准 */
export type Messages = typeof en

/** 译文允许不完整，缺的键回落到英文 */
type Translations = {
  [K in keyof Messages]?: Partial<Messages[K]>
}

// 源语言，同时也是回落语言
const SOURCE_LOCALE = 'en'

const messages: Record<string, Messages | Translations> = {
  en,
  'zh-CN': zhCN,
  'zh-TW': zhTW,
}

// 桌面版 config.json 里 language 的取值（见 util/common/serializer.py 的 LanguageSerializer）
const CONFIG_LOCALE_MAP: Record<string, string> = {
  en_US: 'en',
  zh_CN: 'zh-CN',
  zh_TW: 'zh-TW',
}

// 用 reactive 而非普通变量：切换语言后模板里的 t(...) 要重新求值
const state = reactive({ locale: SOURCE_LOCALE })

function matchBrowserLocale(): string {
  for (const tag of navigator.languages || [navigator.language || '']) {
    if (messages[tag]) {
      return tag
    }

    const lower = tag.toLowerCase()

    // zh-Hant / zh-HK / zh-MO 都归繁体，其余 zh-* 归简体
    if (lower.startsWith('zh')) {
      return /hant|tw|hk|mo/.test(lower) ? 'zh-TW' : 'zh-CN'
    }

    const primary = tag.split('-')[0]

    if (messages[primary]) {
      return primary
    }
  }

  return SOURCE_LOCALE
}

export function currentLocale(): string {
  return state.locale
}

export function availableLocales(): string[] {
  return Object.keys(messages)
}

/**
 * 设置界面语言
 *
 * 传桌面版配置里的值（'Auto' / 'zh_CN' / 'zh_TW' / 'en_US'）或前端的 locale 标签均可，
 * 'Auto' 与无法识别的值都跟随浏览器语言
 */
export function setLocale(value?: string | null): string {
  if (!value || value === 'Auto') {
    state.locale = matchBrowserLocale()

    return state.locale
  }

  const tag = CONFIG_LOCALE_MAP[value] ?? value

  state.locale = messages[tag] ? tag : matchBrowserLocale()

  return state.locale
}

function lookup(bundle: object | undefined, path: string): unknown {
  return path
    .split('.')
    .reduce<unknown>(
      (node, key) => (node == null ? undefined : (node as Record<string, unknown>)[key]),
      bundle,
    )
}

/**
 * 取一条翻译。当前语言缺失时回落到英文源串，仍取不到则原样返回 key，
 * 好让界面上一眼看出漏了哪条
 */
export function t(path: string, params?: Record<string, string | number>): string {
  const text = lookup(messages[state.locale], path) ?? lookup(messages[SOURCE_LOCALE], path)

  if (typeof text !== 'string') {
    return path
  }

  if (!params) {
    return text
  }

  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    params[name] === undefined ? match : String(params[name]),
  )
}

/**
 * 解析列表的列名。后端只给 attr_key，列名在前端维护
 */
export function columnName(key: string): string {
  return t(`column.${key}`)
}

// 首屏先按浏览器语言渲染，拿到桌面版配置后再由 App 调 setLocale 校正
setLocale('Auto')
