import { reactive, shallowReactive } from 'vue'
import en from './en'

export type Messages = typeof en

type Translations = {
  [K in keyof Messages]?: Partial<Messages[K]>
}

const SOURCE_LOCALE = 'en'

/**
 * 有哪些语言
 *
 * **写成常量而不是 `Object.keys(messages)`**：现在只有当前这门语言会被加载，
 * 用已加载的那些去回答「支持哪些语言」，界面上的语言下拉会只剩一项
 */
const LOCALES = ['en', 'zh-CN', 'zh-TW']

/**
 * 除源语言外按需加载
 *
 * 三份文案加起来 100 KB（gzip 34 KB），而一个用户只看得懂其中一份 ——
 * 全打进主包等于让每个人都下两份用不上的。动态 import 让打包器把它们切成独立 chunk。
 *
 * **源语言必须静态导入**：`t()` 是同步的，取不到键时要当场回落到它。
 * 它同时也是首屏还没等到目标语言时的兜底
 */
const LOADERS: Record<string, () => Promise<{ default: Translations }>> = {
  'zh-CN': () => import('./zh-CN'),
  'zh-TW': () => import('./zh-TW'),
}

/**
 * 已加载的文案
 *
 * `shallowReactive`：新加一门语言时要能触发重渲染（`t()` 读的就是这个对象），
 * 但**不能深层代理** —— 这几份是几百个键的嵌套对象，逐层包 Proxy 纯属浪费
 */
const messages = shallowReactive<Record<string, Messages | Translations>>({ en })

// 同一门语言可能被并发要好几次（appStore 读到配置、设置页又改了一次），去重
const loading: Record<string, Promise<void>> = {}

function ensureLoaded(tag: string): Promise<void> {
  if (messages[tag] || !LOADERS[tag]) {
    return Promise.resolve()
  }

  if (!loading[tag]) {
    loading[tag] = LOADERS[tag]()
      .then((module) => {
        messages[tag] = module.default
      })
      .catch((error) => {
        // 加载失败就一直用源语言，界面是英文但不至于白屏。
        // 删掉记录，下次切过来时再试一次
        console.warn(`语言包 ${tag} 加载失败`, error)

        delete loading[tag]
      })
  }

  return loading[tag]
}

/**
 * 等当前语言的文案就位
 *
 * `main.ts` 在挂载之前调一次。少了这一步，中文用户会先看到一瞬间的英文界面 ——
 * 省下来的那点流量不值得拿首屏闪一下去换
 */
export function preloadLocale(): Promise<void> {
  return ensureLoaded(state.locale)
}

const CONFIG_LOCALE_MAP: Record<string, string> = {
  en_US: 'en',
  zh_CN: 'zh-CN',
  zh_TW: 'zh-TW',
}

const state = reactive({ locale: SOURCE_LOCALE })

function matchBrowserLocale(): string {
  for (const tag of navigator.languages || [navigator.language || '']) {
    if (LOCALES.includes(tag)) {
      return tag
    }

    const lower = tag.toLowerCase()

    if (lower.startsWith('zh')) {
      return /hant|tw|hk|mo/.test(lower) ? 'zh-TW' : 'zh-CN'
    }

    const primary = tag.split('-')[0]

    if (LOCALES.includes(primary)) {
      return primary
    }
  }

  return SOURCE_LOCALE
}

export function currentLocale(): string {
  return state.locale
}

export function availableLocales(): string[] {
  return [...LOCALES]
}

/**
 * 切换语言。**仍然是同步的** —— 两个调用点都是即发即忘，改成 async 会把
 * 「换语言」这件事传染成一串 await
 *
 * 文案还没到时先用源语言顶着，到了之后 `messages` 是响应式的，界面自己会跟上
 */
export function setLocale(value?: string | null): string {
  if (!value || value === 'Auto') {
    state.locale = matchBrowserLocale()
  } else {
    const tag = CONFIG_LOCALE_MAP[value] ?? value

    state.locale = LOCALES.includes(tag) ? tag : matchBrowserLocale()
  }

  void ensureLoaded(state.locale)

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
