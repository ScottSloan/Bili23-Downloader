import { defineStore } from 'pinia'

const DEFAULT_PRIMARY_COLOR = '#009faa'

// 默认跟随系统，与 GUI 一致（config.py 里 config.themeMode.value = Theme.AUTO）
const DEFAULT_MODE = 'auto'

const DARK_MEDIA_QUERY = '(prefers-color-scheme: dark)'

// localStorage 键名 —— index.html 里的首屏引导脚本必须用同一套，改这里就要同步改那边
const STORAGE_KEY_MODE = 'bili23.theme.mode'
const STORAGE_KEY_PRIMARY = 'bili23.theme.primary-color'
const STORAGE_KEY_PALETTE = 'bili23.theme.palette'

interface Rgb {
  r: number
  g: number
  b: number
}

interface Hsv {
  h: number
  s: number
  v: number
}

type Tone = 'primary' | 'dark1' | 'dark2' | 'dark3' | 'light1' | 'light2' | 'light3'

type ThemeName = 'light' | 'dark'

/** 用户可选的三态：显式浅色 / 显式深色 / 跟随系统 */
type ThemeMode = ThemeName | 'auto'

type Palette = Record<Tone, string>

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value))
}

function normalizeHexColor(color: unknown): string {
  if (typeof color !== 'string') {
    return DEFAULT_PRIMARY_COLOR
  }

  const value = color.trim()
  if (!value) {
    return DEFAULT_PRIMARY_COLOR
  }

  if (/^#[0-9a-fA-F]{3}$/.test(value)) {
    return `#${value
      .slice(1)
      .split('')
      .map((char) => char + char)
      .join('')}`
  }

  if (/^#[0-9a-fA-F]{6}$/.test(value)) {
    return value.toLowerCase()
  }

  return DEFAULT_PRIMARY_COLOR
}

function hexToRgb(hex: string): Rgb {
  const value = normalizeHexColor(hex).slice(1)
  const number = Number.parseInt(value, 16)

  return {
    r: (number >> 16) & 255,
    g: (number >> 8) & 255,
    b: number & 255,
  }
}

function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (value: number) => Math.round(value).toString(16).padStart(2, '0')
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}

function rgbToHsv(r: number, g: number, b: number): Hsv {
  const red = r / 255
  const green = g / 255
  const blue = b / 255

  const max = Math.max(red, green, blue)
  const min = Math.min(red, green, blue)
  const delta = max - min

  let hue = 0
  const saturation = max === 0 ? 0 : delta / max
  const value = max

  if (delta !== 0) {
    if (max === red) {
      hue = ((green - blue) / delta) % 6
    } else if (max === green) {
      hue = (blue - red) / delta + 2
    } else {
      hue = (red - green) / delta + 4
    }

    hue *= 60
    if (hue < 0) {
      hue += 360
    }
  }

  return { h: hue, s: saturation, v: value }
}

function hsvToRgb(h: number, s: number, v: number): Rgb {
  const chroma = v * s
  const x = chroma * (1 - Math.abs(((h / 60) % 2) - 1))
  const match = v - chroma

  let red = 0
  let green = 0
  let blue = 0

  if (h >= 0 && h < 60) {
    red = chroma
    green = x
  } else if (h < 120) {
    red = x
    green = chroma
  } else if (h < 180) {
    green = chroma
    blue = x
  } else if (h < 240) {
    green = x
    blue = chroma
  } else if (h < 300) {
    red = x
    blue = chroma
  } else {
    red = chroma
    blue = x
  }

  return {
    r: (red + match) * 255,
    g: (green + match) * 255,
    b: (blue + match) * 255,
  }
}

/**
 * 由用户配置的主色推导出整套色阶
 *
 * 只产出主题色，界面的背景 / 文字 / 描边一律走 styles/tokens.css 里的 design token，
 * 不在这里注入 —— 那些值是固定的，没必要每次切主题都用 JS 写一遍
 */
function generateThemePalette(primaryColor: string, isDark: boolean): Palette {
  const { r, g, b } = hexToRgb(primaryColor)
  const { h, s, v } = rgbToHsv(r, g, b)

  const createTone = (tone: Tone): string => {
    let saturation = s
    let value = v

    if (isDark) {
      saturation *= 0.84
      value = 1

      if (tone === 'dark1') {
        value *= 0.9
      } else if (tone === 'dark2') {
        saturation *= 0.977
        value *= 0.82
      } else if (tone === 'dark3') {
        saturation *= 0.95
        value *= 0.7
      } else if (tone === 'light1') {
        saturation *= 0.92
      } else if (tone === 'light2') {
        saturation *= 0.78
      } else if (tone === 'light3') {
        saturation *= 0.65
      }
    } else {
      if (tone === 'dark1') {
        value *= 0.75
      } else if (tone === 'dark2') {
        saturation *= 1.05
        value *= 0.5
      } else if (tone === 'dark3') {
        saturation *= 1.1
        value *= 0.4
      } else if (tone === 'light1') {
        value *= 1.05
      } else if (tone === 'light2') {
        saturation *= 0.75
        value *= 1.05
      } else if (tone === 'light3') {
        saturation *= 0.65
        value *= 1.05
      }
    }

    const rgb = hsvToRgb(h, clamp01(saturation), clamp01(value))
    return rgbToHex(rgb.r, rgb.g, rgb.b)
  }

  const tones = {
    primary: createTone('primary'),
    dark1: createTone('dark1'),
    dark2: createTone('dark2'),
    dark3: createTone('dark3'),
    light1: createTone('light1'),
    light2: createTone('light2'),
    light3: createTone('light3'),
  }

  return tones
}

/** 主题色最终写到根节点上的 CSS 变量。键名同时也是首屏缓存里的键 */
function paletteToCssVariables(palette: Palette): Record<string, string> {
  return {
    '--primary-color': palette.primary,
    '--primary-color-dark-1': palette.dark1,
    '--primary-color-dark-2': palette.dark2,
    '--primary-color-dark-3': palette.dark3,
    '--primary-color-light-1': palette.light1,
    '--primary-color-light-2': palette.light2,
    '--primary-color-light-3': palette.light3,
  }
}

/**
 * 换主题时把过渡整体关掉一小会儿
 *
 * ## 不关会怎样
 *
 * **切完主题，凡是带 `transition` 的控件颜色都不更新，非刷新页面不可。**
 * 实测：切到深色后 `:root` 上的 `--primary-color` 已经是新值，元素也确实继承到了新值，
 * 但它自己的 `background-color` 仍然算成旧的那一个；把该元素的 `transition` 摘掉再读，
 * 立刻跳回正确值。
 *
 * 原因是浏览器为「值来自 var() 而 var 在祖先上被改掉」的属性起了一次过渡，
 * 而那次过渡的终点是旧值，于是就永远停在原地。**这一条静默且到处都是** ——
 * 按钮、输入框、开关、卡片……凡是为了手感加了 transition 的地方全中招。
 *
 * ## 顺带的好处
 *
 * 就算没这个问题，整页颜色一起做 200ms 渐变本来也不好看：深浅之间每个控件各渐各的，
 * 中途会闪过一堆不属于任何一套主题的中间色。换主题就该是一帧切过去。
 *
 * 关两帧再放开：一帧用来让「无过渡」生效，另一帧用来让新颜色以无过渡的方式画上去。
 *
 * **不能只靠 rAF 放开**：标签页切到后台时浏览器根本不跑 rAF，那两个回调会一直排着，
 * 类就永久留在根节点上 —— 回到这一页时全站过渡都是死的，而且看不出是谁干的
 * （实测过，`document.visibilityState` 一 hidden 就复现）。所以再挂一个定时器兜底，
 * 谁先到算谁的。
 */
function suppressTransitions() {
  const root = document.documentElement

  root.classList.add('theme-switching')

  const release = () => root.classList.remove('theme-switching')

  requestAnimationFrame(() => requestAnimationFrame(release))

  setTimeout(release, 120)
}

/** 首屏那次不做过场：一进页面就看见一次淡入淡出很奇怪 */
let themeApplied = false

type StartViewTransition = (callback: () => void) => unknown

/**
 * 换主题时整页交叉淡化
 *
 * **不能靠各控件自己的 `transition` 来做渐变**：根节点上的自定义属性变了之后，
 * 带过渡的属性会卡在旧值上不更新（见 suppressTransitions 的说明），
 * 所以那条路是先把过渡全关掉、瞬间切过去的。
 *
 * 要渐变就换一层做：View Transitions 把切换前的画面截成一张图，与切换后的画面
 * 在合成层交叉淡化。它**不关心颜色是怎么算出来的**，自然也就不受那个坑影响，
 * 而且整页一起淡，不会出现各控件各渐各的、中途闪过一堆中间色。
 *
 * 浏览器不支持（Chromium 111 以前、以及一些别的内核）就直接切，
 * 跟着系统「减少动态效果」的设置也直接切
 */
function withViewTransition(commit: () => void) {
  const start = (document as Document & { startViewTransition?: StartViewTransition })
    .startViewTransition

  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  if (!themeApplied || reduced || typeof start !== 'function') {
    themeApplied = true

    commit()

    return
  }

  start.call(document, commit)
}

function applyThemeVariables(theme: ThemeName, primaryColor: string) {
  if (typeof document === 'undefined') {
    return
  }

  const root = document.documentElement
  const variables = paletteToCssVariables(generateThemePalette(primaryColor, theme === 'dark'))

  withViewTransition(() => {
    suppressTransitions()

    root.dataset.theme = theme
    root.style.setProperty('--theme-mode', theme)

    for (const [name, value] of Object.entries(variables)) {
      root.style.setProperty(name, value)
    }

    // 强制同步一次样式计算：新值必须在「过渡还关着」的这一帧里落定，
    // 否则浏览器会把变量更新与去掉 theme-switching 合并到同一帧，等于没关
    void root.offsetHeight
  })
}

// localStorage 读写一律包 try/catch：隐私模式、或浏览器禁用了站点数据时，
// 连 getItem 都会直接抛异常，不能让它拦住整个应用启动
function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // 存不下只是下次刷新回到默认值，不影响本次会话
  }
}

function systemTheme(): ThemeName {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return 'light'
  }

  return window.matchMedia(DARK_MEDIA_QUERY).matches ? 'dark' : 'light'
}

const THEME_MODES: ThemeMode[] = ['light', 'dark', 'auto']

function normalizeMode(value: unknown): ThemeMode {
  return THEME_MODES.find((mode) => mode === value) ?? DEFAULT_MODE
}

function resolveTheme(mode: ThemeMode): ThemeName {
  return mode === 'auto' ? systemTheme() : mode
}

/**
 * 把两套主题下的色阶都算好存进 localStorage，供 index.html 的首屏引导脚本直接回填
 *
 * 首屏那段脚本要在任何模块加载前就把颜色写上去（否则会闪一下），但色阶推导的 HSV 运算
 * 不适合复制一份到 index.html 里 —— 两处算法一旦走偏就是难查的色差。
 * 所以这里把结果缓存下来，首屏只做「读 + 回填」，算法仍然只有这一份。
 *
 * 缓存丢了也不影响正确性：首屏退回 theme.css 里的默认主题色，
 * store 初始化时会立刻按真实配置重算并覆盖。
 */
function persistPalette(primaryColor: string) {
  const cache = {
    light: paletteToCssVariables(generateThemePalette(primaryColor, false)),
    dark: paletteToCssVariables(generateThemePalette(primaryColor, true)),
  }

  writeStorage(STORAGE_KEY_PALETTE, JSON.stringify(cache))
}

// matchMedia 的监听只注册一次。store 是单例，重复注册会让系统切一次主题触发多次重绘
let systemThemeWatched = false

interface ThemeState {
  /** 用户选的模式，auto 表示跟随系统 —— 与 GUI 的 Theme.AUTO 对齐 */
  mode: ThemeMode
  /** mode 解析之后实际生效的主题，写到根节点的 data-theme 上 */
  theme: ThemeName
  isDark: boolean
  primaryColor: string
}

export const useThemeStore = defineStore('theme', {
  // 初始值直接取自 localStorage，而不是先给默认值再在 onMounted 里改回来 ——
  // 后者会让界面上的主题选中态先闪一下错的
  state: (): ThemeState => {
    const mode = normalizeMode(readStorage(STORAGE_KEY_MODE))
    const theme = resolveTheme(mode)

    return {
      mode,
      theme,
      isDark: theme === 'dark',
      primaryColor: normalizeHexColor(readStorage(STORAGE_KEY_PRIMARY)),
    }
  },

  actions: {
    /** 应用启动时调一次：补齐首屏缓存，并开始监听系统主题 */
    initialize() {
      this.syncThemeVariables()
      persistPalette(this.primaryColor)

      if (systemThemeWatched || typeof window === 'undefined' || !window.matchMedia) {
        return
      }

      systemThemeWatched = true

      window.matchMedia(DARK_MEDIA_QUERY).addEventListener('change', () => {
        // 只有跟随系统时才响应；用户显式选了浅色 / 深色就不该被系统设置改掉
        if (this.mode === 'auto') {
          this.syncThemeVariables()
        }
      })
    },

    /** 按当前 mode 重新解析主题并写到根节点上 */
    syncThemeVariables() {
      this.theme = resolveTheme(this.mode)
      this.isDark = this.theme === 'dark'

      applyThemeVariables(this.theme, this.primaryColor)
    },

    setMode(mode: string) {
      this.mode = normalizeMode(mode)

      writeStorage(STORAGE_KEY_MODE, this.mode)
      this.syncThemeVariables()
    },

    /** 显式指定浅色 / 深色，等价于把模式切成对应的那一档 */
    setTheme(theme: string) {
      this.setMode(theme === 'dark' ? 'dark' : 'light')
    },

    toggleTheme() {
      this.setTheme(this.isDark ? 'light' : 'dark')
    },

    setPrimaryColor(color: string) {
      this.primaryColor = normalizeHexColor(color)

      writeStorage(STORAGE_KEY_PRIMARY, this.primaryColor)
      persistPalette(this.primaryColor)
      this.syncThemeVariables()
    },
  },
})
