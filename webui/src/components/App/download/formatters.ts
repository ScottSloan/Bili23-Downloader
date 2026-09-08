// 下载列表的显示格式，与 GUI 的 util/format/units.py、util/format/time.py 保持一致

/**
 * 文件大小
 *
 * 对齐 `Units.format_file_size`：1024 进制、保留两位小数、不足 1KB 显示 B。
 * **两位小数不是随手定的** —— 桌面版列表里就是 `15.80 MB / 19.49 MB`，
 * 少一位会让进度看起来一跳一跳的
 */
export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']

  let value = bytes > 0 ? bytes : 0
  let index = 0

  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }

  // 连 B 也带两位小数，`format_file_size` 就是这么写的（`0.00 B`）
  return `${value.toFixed(2)} ${units[index]}`
}

/** 速度。0 显示空串 —— 桌面版没在下的时候那一格就是空的，不是「0 B/s」 */
export function formatSpeed(bytes: number): string {
  if (!bytes || bytes <= 0) {
    return ''
  }

  return `${formatFileSize(bytes)}/s`
}

/**
 * 完成时间
 *
 * 桌面版 `getInfoText` 用的是 `Time.format_timestamp` 的默认格式，
 * 带到秒（`%Y-%m-%d %H:%M:%S`）—— 与解析列表那个只到日的不是一回事
 */
export function formatTimestamp(timestamp: number): string {
  if (!timestamp) {
    return ''
  }

  const date = new Date(timestamp * 1000)

  const pad = (value: number) => String(value).padStart(2, '0')

  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    ` ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}
