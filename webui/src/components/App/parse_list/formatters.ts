import type { ParseNode } from '@/api/types'

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

    case 'dyn_time':
      return formatDate(node.dyn_time)

    default:
      return String((node as unknown as Record<string, unknown>)[key] ?? '')
  }
}
