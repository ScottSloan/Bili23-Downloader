// ASS 颜色字符串与 #rrggbb + 不透明度之间的互转
//
// **这是 `src/util/common/color.py` 的一份平行实现**，不是抄错了 —— 颜色选择器在浏览器里，
// 每拖一下都往服务端问一次转换是荒唐的。但两份实现走偏就是「保存后颜色变了」这种
// 没有报错的故障，所以 `test/ass_color.py` 会拿 node 跑这份实现，
// 与 Python 那份逐值对照（含边界与畸形输入）。改这里就要跑那个脚本。
//
// 格式是 `&HAABBGGRR`：
//
// - **字节序与常见的 RGB 相反**（BB GG RR）
// - **AA 位是「透明度」而非「不透明度」**：00 完全不透明、FF 完全透明
//
// 两点各自反了一次，凭直觉写必错。

export interface RgbaColor {
  /** #rrggbb，给 `<input type="color">` 用 */
  hex: string
  /** 0–255 的不透明度，255 为完全不透明 —— 与 CSS 一致，与 ASS 相反 */
  alpha: number
}

function clampByte(value: number): number {
  if (!Number.isFinite(value)) {
    return 0
  }

  return Math.min(255, Math.max(0, Math.round(value)))
}

/**
 * `&HAABBGGRR` → `{ hex, alpha }`
 *
 * 认不出来的输入退回不透明的黑色。配置里确实存在畸形值 —— 默认配置里
 * `subtitle_style.color.border` 就是 `"H00000000"`（少一个 `&`），
 * Python 那边用 `lstrip("&H")` 一并吃掉了，这里也要一样宽容
 */
export function assToRgba(ass: unknown): RgbaColor {
  const text = typeof ass === 'string' ? ass.replace(/^[&H]+/, '') : ''

  if (!/^[0-9a-fA-F]{8}$/.test(text)) {
    return { hex: '#000000', alpha: 255 }
  }

  const a = Number.parseInt(text.slice(0, 2), 16)
  const b = text.slice(2, 4)
  const g = text.slice(4, 6)
  const r = text.slice(6, 8)

  return { hex: `#${r}${g}${b}`.toLowerCase(), alpha: 255 - a }
}

/** `{ hex, alpha }` → `&HAABBGGRR` */
export function rgbaToAss(hex: string, alpha: number): string {
  const text = (hex || '').replace(/^#/, '')

  const value = /^[0-9a-fA-F]{6}$/.test(text) ? text : '000000'

  const r = value.slice(0, 2)
  const g = value.slice(2, 4)
  const b = value.slice(4, 6)

  const a = (255 - clampByte(alpha)).toString(16).padStart(2, '0')

  // Python 那边是 f"&H{...:02X}" —— 十六进制大写，这里必须一致，
  // 否则同一个颜色在两端存进 config.json 的字符串不同，diff 里会莫名其妙多出改动
  return `&H${a}${b}${g}${r}`.toUpperCase()
}
