import type { ParseNode } from '@/api'

// 列的显示格式，与 GUI 的 gui/component/parse_list/header.py 保持一致

export function formatDuration(seconds: number): string {
  if (!seconds) {
    return ''
  }

  const total = Math.floor(seconds)

  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60

  const pad = (value: number) => String(value).padStart(2, '0')

  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(secs)}` : `${minutes}:${pad(secs)}`
}

export function formatDate(timestamp: number): string {
  if (!timestamp) {
    return ''
  }

  const date = new Date(timestamp * 1000)

  const pad = (value: number) => String(value).padStart(2, '0')

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function cellText(node: ParseNode, key: string): string {
  switch (key) {
    case 'duration':
      return formatDuration(node.duration)

    // 后端不再合成 dyn_time，改为分别给三个时间字段：
    // 投稿视频看发布时间、收藏夹看收藏时间、历史记录看观看时间。
    // 哪个有值就显示哪个 —— 同一列在不同来源下本就是不同的含义
    case 'dyn_time':
      return formatDate(node.pubtime || node.favtime || node.viewtime || 0)

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
