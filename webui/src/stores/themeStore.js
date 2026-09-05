import { defineStore } from 'pinia'

const DEFAULT_PRIMARY_COLOR = '#009faa'

function clamp01(value) {
  return Math.max(0, Math.min(1, value))
}

function normalizeHexColor(color) {
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

function hexToRgb(hex) {
  const value = normalizeHexColor(hex).slice(1)
  const number = Number.parseInt(value, 16)

  return {
    r: (number >> 16) & 255,
    g: (number >> 8) & 255,
    b: number & 255,
  }
}

function rgbToHex(r, g, b) {
  const toHex = (value) => Math.round(value).toString(16).padStart(2, '0')
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}

function rgbToHsv(r, g, b) {
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

function hsvToRgb(h, s, v) {
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

function generateThemePalette(primaryColor, isDark) {
  const { r, g, b } = hexToRgb(primaryColor)
  const { h, s, v } = rgbToHsv(r, g, b)

  const createTone = (tone) => {
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

  const palette = {
    primary: createTone('primary'),
    dark1: createTone('dark1'),
    dark2: createTone('dark2'),
    dark3: createTone('dark3'),
    light1: createTone('light1'),
    light2: createTone('light2'),
    light3: createTone('light3'),
  }

  palette.surface = isDark ? '#1f1f1f' : '#f0f4f9'
  palette.surfaceHover = isDark ? '#2a2a2a' : '#f9f9f9'
  palette.text = isDark ? '#ffffff' : '#000000'

  return palette
}

function applyThemeVariables(theme, primaryColor) {
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
  root.style.setProperty('--theme-surface', palette.surface)
  root.style.setProperty('--theme-surface-hover', palette.surfaceHover)
  root.style.setProperty('--theme-text-color', palette.text)
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: 'light',
    isDark: false,
    primaryColor: DEFAULT_PRIMARY_COLOR,
  }),

  actions: {
    toggleTheme() {
      this.setTheme(this.isDark ? 'light' : 'dark')
    },

    setTheme(theme) {
      this.theme = theme === 'dark' ? 'dark' : 'light'
      this.isDark = this.theme === 'dark'
      applyThemeVariables(this.theme, this.primaryColor)
    },

    setPrimaryColor(color) {
      this.primaryColor = normalizeHexColor(color)
      applyThemeVariables(this.theme, this.primaryColor)
    },

    syncThemeVariables() {
      applyThemeVariables(this.theme, this.primaryColor)
    },
  },
})
