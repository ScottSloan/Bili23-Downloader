import { reactive } from 'vue'
import en from './en'
import zhCN from './zh-CN'
import zhTW from './zh-TW'

export type Messages = typeof en

type Translations = {
  [K in keyof Messages]?: Partial<Messages[K]>
}

const SOURCE_LOCALE = 'en'

const messages: Record<string, Messages | Translations> = {
  en,
  'zh-CN': zhCN,
  'zh-TW': zhTW,
}

const CONFIG_LOCALE_MAP: Record<string, string> = {
  en_US: 'en',
  zh_CN: 'zh-CN',
  zh_TW: 'zh-TW',
}

const state = reactive({ locale: SOURCE_LOCALE })

function matchBrowserLocale(): string {
  for (const tag of navigator.languages || [navigator.language || '']) {
    if (messages[tag]) {
      return tag
    }

    const lower = tag.toLowerCase()

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


export function columnName(key: string): string {
  return t(`column.${key}`)
}

export function episodeTypeName(key: string): string {
  if (!key) {
    return ''
  }

  const text = t(`episodeType.${key}`)

  return text === `episodeType.${key}` ? key : text
}


export function mediaLabel(group: string, value: string | number, fallback = ''): string {
  const key = `media.${group}.${value}`
  const text = t(key)

  if (text !== key) {
    return text
  }

  return fallback || String(value)
}

setLocale('Auto')
