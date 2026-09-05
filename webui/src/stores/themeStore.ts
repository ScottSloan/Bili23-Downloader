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

function applyThemeVariables(theme: ThemeName, primaryColor: string) {
  if (typeof document === 'undefined') {
    return
  }

  const root = document.documentElement
  const variables = paletteToCssVariables(generateThemePalette(primaryColor, theme === 'dark'))

  root.dataset.theme = theme
  root.style.setProperty('--theme-mode', theme)

  for (const [name, value] of Object.entries(variables)) {
    root.style.setProperty(name, value)
  }
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
