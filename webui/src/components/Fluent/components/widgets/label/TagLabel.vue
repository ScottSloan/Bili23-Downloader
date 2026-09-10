<script setup lang="ts">
/**
 * 圆角矩形的彩色标签
 *
 * 对应 `gui/component/widget/label.py` 的 `TagLabel`：下载选项对话框底部那排
 * 「视频 / 音频 / 弹幕…」用的就是它。高 20、字号 11、圆角 4，配色由一个主题色推出来。
 *
 * ## 三种颜色都是算出来的，不是各写一遍
 *
 * 桌面版给的只有一个主题色，文字 / 底色 / 描边分别是：
 *
 * | | 文字 | 底色 | 描边 |
 * |---|---|---|---|
 * | 浅色 | `darker(135)` | 12% | 35% |
 * | 深色 | `lighter(150)` | 25% | 50% |
 *
 * 底色与描边直接用 `color-mix()` 兑透明度；文字那两档是 Qt 的 HSV 明度缩放，
 * CSS 没有等价物，所以照着 `QColor::darker` / `lighter` 移植了一份（见 shade()）。
 * **不能用 `filter: brightness()` 糊弄** —— 那个作用在 sRGB 三通道上，
 * 与 Qt 在 HSV 的 V 上缩放算出来的不是一个颜色，深色主题下几个标签会明显偏色。
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    text: string
    /** 主题色，`#RRGGBB` */
    color?: string
  }>(),
  {
    color: '#0078D4',
  },
)

interface Rgb {
  r: number
  g: number
  b: number
}

function parse(hex: string): Rgb {
  const value = hex.replace('#', '')

  const full =
    value.length === 3
      ? value
          .split('')
          .map((char) => char + char)
          .join('')
      : value

  const int = Number.parseInt(full, 16)

  return Number.isNaN(int)
    ? { r: 0, g: 120, b: 212 }
    : { r: (int >> 16) & 255, g: (int >> 8) & 255, b: int & 255 }
}

/**
 * Qt 的 `QColor::darker(factor)` / `lighter(factor)`
 *
 * 两者都是在 HSV 的 V 上缩放：darker 是 `v * 100 / factor`，lighter 是 `v * factor / 100`。
 *
 * **lighter 溢出时要减饱和度**，这一步不能省：`#0078D4` 的 V 已经是 212，
 * 乘 1.5 之后早就超了 255，Qt 会把超出的部分从饱和度里扣掉，结果是一个更浅、
 * 更接近白的蓝。只做钳位的话得到的是纯度不变的深蓝，在深色底上根本看不清。
 *
 * Qt 内部用 16 位存 HSV，扣饱和度的量也按 16 位算，所以这里跟着换算（× 257）
 */
function shade(rgb: Rgb, factor: number): Rgb {
  const [h, s, v] = toHsv(rgb)

  if (factor < 100) {
    // 与 Qt 一致：lighter(小于 100) 等价于 darker(10000 / factor)
    return shade(rgb, 10000 / factor)
  }

  if (factor === 100) {
    return rgb
  }

  return factor > 100 ? fromHsv(...lighten(h, s, v, factor)) : rgb
}

function lighten(h: number, s: number, v: number, factor: number): [number, number, number] {
  let value16 = Math.round((v * 257 * factor) / 100)
  let sat16 = s * 257

  if (value16 > 65535) {
    sat16 = Math.max(0, sat16 - (value16 - 65535))
    value16 = 65535
  }

  return [h, sat16 / 257, value16 / 257]
}

function darken(rgb: Rgb, factor: number): Rgb {
  const [h, s, v] = toHsv(rgb)

  return fromHsv(h, s, (v * 100) / factor)
}

function toHsv({ r, g, b }: Rgb): [number, number, number] {
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const delta = max - min

  let h = 0

  if (delta !== 0) {
    if (max === r) {
      h = ((g - b) / delta) % 6
    } else if (max === g) {
      h = (b - r) / delta + 2
    } else {
      h = (r - g) / delta + 4
    }

    h *= 60

    if (h < 0) {
      h += 360
    }
  }

  return [h, max === 0 ? 0 : (delta / max) * 255, max]
}

function fromHsv(h: number, s: number, v: number): Rgb {
  const saturation = Math.min(255, Math.max(0, s)) / 255
  const value = Math.min(255, Math.max(0, v))

  const c = value * saturation
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = value - c

  const table: Rgb[] = [
    { r: c, g: x, b: 0 },
    { r: x, g: c, b: 0 },
    { r: 0, g: c, b: x },
    { r: 0, g: x, b: c },
    { r: x, g: 0, b: c },
    { r: c, g: 0, b: x },
  ]

  const picked = table[Math.min(5, Math.floor(((h % 360) + 360) % 360 / 60))]

  // 与 Qt 对过：8 个标签色 × 明暗两档共 48 个分量，只有 3 个差 1/255
  // （Qt 内部用 16 位存 HSV，取 8 位分量时是 `>> 8` 的截断）。
  // 试过改成 Math.floor 去贴那 3 个，结果是另外十几个反而偏了 —— 四舍五入更接近
  return {
    r: Math.round(picked.r + m),
    g: Math.round(picked.g + m),
    b: Math.round(picked.b + m),
  }
}

function css({ r, g, b }: Rgb): string {
  return `rgb(${r}, ${g}, ${b})`
}

const rgb = computed(() => parse(props.color))

/** 浅色主题压暗文字，否则亮色系标签（青、绿）的文字在白底上几乎看不清 */
const lightText = computed(() => css(darken(rgb.value, 135)))

/** 深色主题提亮文字 */
const darkText = computed(() => css(shade(rgb.value, 150)))

const base = computed(() => {
  const { r, g, b } = rgb.value

  return `${r}, ${g}, ${b}`
})
</script>

<template>
  <span
    class="tag-label"
    :style="{
      '--tag-base': base,
      '--tag-text-light': lightText,
      '--tag-text-dark': darkText,
    }"
  >
    {{ text }}
  </span>
</template>

<style scoped>
.tag-label {
  display: inline-flex;
  align-items: center;
  box-sizing: border-box;
  height: 20px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
  user-select: none;

  color: var(--tag-text-light);
  background-color: rgba(var(--tag-base), 0.12);
  border: 1px solid rgba(var(--tag-base), 0.35);
}

/*
  深色主题下底色与描边都要更实一些（12/35 → 25/50）：同样的透明度铺在深底上
  几乎看不出来，桌面版也是分了两档。

  只判 `data-theme`，不另外写 `prefers-color-scheme`：themeStore 会把 auto 解析成
  具体的一种再写到根节点上，根节点永远带着这个属性（与本项目其它组件一致）
*/
:root[data-theme='dark'] .tag-label {
  color: var(--tag-text-dark);
  background-color: rgba(var(--tag-base), 0.25);
  border-color: rgba(var(--tag-base), 0.5);
}
</style>
