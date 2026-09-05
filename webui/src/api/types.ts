// 后端接口的数据契约
//
// S0 阶段手写。S3 换成 FastAPI 之后改由 openapi-typescript 从 OpenAPI 生成，
// 届时本文件删除（见 docs/webui/PLAN.md 的 S3-12）。

/** 勾选态，与桌面版的 Qt.CheckState 对齐 */
export const UNCHECKED = 0
export const PARTIAL = 1
export const CHECKED = 2

export type CheckState = typeof UNCHECKED | typeof PARTIAL | typeof CHECKED

/** 解析列表的一列。列名不在这里，由前端 i18n 按 key 提供（D12） */
export interface ParseColumn {
  /** 与桌面版 config 的 parse_list_column[].attr_key 一致 */
  key: string
  width: number
  show: boolean
}

export interface ParseNode {
  /** 位置路径（"1"、"1.2"），不是 episode_id —— 后者同一视频的所有分P 共享 */
  id: string
  title: string
  /** 树节点上是分组标签（"番剧"、"章节"），条目上才是序号 */
  number: string | number
  badge: string
  /** 秒 */
  duration: number
  /** Unix 时间戳；按内容类型分别取发布 / 收藏 / 观看时间 */
  dyn_time: number
  checked: CheckState
  /** true 表示只是分组用的节点，本身不可下载 */
  is_node: boolean
  cover?: string
  /** 个人空间、收藏夹里的视频，需要二次解析才能下载 */
  needs_reparse?: boolean
  already_downloaded?: boolean
  children?: ParseNode[]
}

export interface ParseTreePayload {
  category: string
  /** 可下载条目数，不含分组节点 */
  total: number
  tree: ParseNode[]
  columns: ParseColumn[]
  /** 仅在媒体信息取不到时出现 */
  media_info_available?: false
  media_info_error?: string
  /** 本次解析实际可选的画质 / 音质 / 编码 */
  available?: Record<string, string[]>
}

export interface StatusPayload {
  version: string
  /** 桌面版配置里的取值：'Auto' | 'zh_CN' | 'zh_TW' | 'en_US' */
  language: string
  logged_in: boolean
  uname: string
  uid: string | number
  parse_ready: boolean
  columns: ParseColumn[]
}
