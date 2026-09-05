import { defineStore } from 'pinia'

const DEFAULT_PRIMARY_COLOR = '#009faa'

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

function applyThemeVariables(theme: ThemeName, primaryColor: string) {
  if (typeof document === 'undefined') {
    return
  }

  const isDark = theme === 'dark'
  const palette = generateThemePalette(primaryColor, isDark)
  const root = document.documentElement

  root.dataset.theme = theme
  root.style.setProperty('--theme-mode', theme)
  root.style.setProperty('--primary-color', palette.primary)
  root.style.setProperty('--primary-color-dark-1', palette.dark1)
  root.style.setProperty('--primary-color-dark-2', palette.dark2)
  root.style.setProperty('--primary-color-dark-3', palette.dark3)
  root.style.setProperty('--primary-color-light-1', palette.light1)
  root.style.setProperty('--primary-color-light-2', palette.light2)
  root.style.setProperty('--primary-color-light-3', palette.light3)
}

export const useThemeStore = defineStore('theme', {
  state: (): { theme: ThemeName; isDark: boolean; primaryColor: string } => ({
    theme: 'light',
    isDark: false,
    primaryColor: DEFAULT_PRIMARY_COLOR,
  }),

  actions: {
    toggleTheme() {
      this.setTheme(this.isDark ? 'light' : 'dark')
    },

    setTheme(theme: string) {
      this.theme = theme === 'dark' ? 'dark' : 'light'
      this.isDark = this.theme === 'dark'
      applyThemeVariables(this.theme, this.primaryColor)
    },

    setPrimaryColor(color: string) {
      this.primaryColor = normalizeHexColor(color)
      applyThemeVariables(this.theme, this.primaryColor)
    },

    syncThemeVariables() {
      applyThemeVariables(this.theme, this.primaryColor)
    },
  },
})
