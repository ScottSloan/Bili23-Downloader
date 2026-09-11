import { episodeTypeName } from '@/i18n'
import type { ParseNode } from '@/api'

// 列的显示格式，与 GUI 的 gui/component/parse_list/header.py 保持一致

/**
 * 时长
 *
 * 与 `util/format/units.py` 的 `format_duration` 逐位对齐：**分钟也补零**
 * （`03:40` 而不是 `3:40`），有小时才显示小时。0 显示为空
 */
export function formatDuration(seconds: number): string {
  if (!seconds) {
    return ''
  }

  const total = Math.floor(seconds)

  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60

  const pad = (value: number) => String(value).padStart(2, '0')

  return hours > 0 ? `${pad(hours)}:${pad(minutes)}:${pad(secs)}` : `${pad(minutes)}:${pad(secs)}`
}

/**
 * 日期
 *
 * 只到日，不带时分 —— 与 `header.py` 的 `DateFormatter` 一致（那边是 `%Y-%m-%d`）。
 * 列宽就那么点，带上时分会被截断，而具体到分钟对这一列也没有意义
 */
export function formatDate(timestamp: number): string {
  if (!timestamp) {
    return ''
  }

  const date = new Date(timestamp * 1000)

  const pad = (value: number) => String(value).padStart(2, '0')

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function cellText(node: ParseNode, key: string): string {
  switch (key) {
    // 分组行的序号列显示的是剧集类型（番剧 / 收藏夹 / 个人空间…）。
    // 后端给的 `number` 是翻过的字面量，但服务端没装 Qt 的翻译函数，那是英文；
    // 它同时给了稳定的键，前端自己查表（D12）
    case 'number':
      return node.number_key
        ? episodeTypeName(node.number_key)
        : String(node.number ?? '')

    case 'duration':
      return formatDuration(node.duration)

    // 这一列在不同来源下是不同的含义（投稿看发布时间、收藏夹看收藏时间、
    // 历史记录看观看时间）。**该显示哪一个由后端挑好**（`TreeItem.dyn_time`，
    // 按 Attribute 位判断）—— 这边「哪个有值用哪个」看似等价，实则不是：
    // 收藏夹的条目两个时间都有，那样会显示成发布时间
    case 'dyn_time':
      return formatDate(node.dyn_time || 0)

    case 'pubtime':
      return formatDate(node.pubtime || 0)

    case 'favtime':
      return formatDate(node.favtime || 0)

    case 'viewtime':
      return formatDate(node.viewtime || 0)

    default:
      return String((node as unknown as Record<string, unknown>)[key] ?? '')
  }
}
