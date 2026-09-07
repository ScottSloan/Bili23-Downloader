// 按域分组的接口调用
//
// 每个函数的入参与返回都从 `schema.d.ts` 推出来，**没有一处手写的结构**。
// 后端改了字段，这里会直接编译不过 —— 那正是要的效果（S3-12 加 `--check` 也是这个目的）。

import { get, post } from './client'
import type { Ok, Body } from './client'

// ---------------- 类型别名 ----------------
//
// 组件里到处写 `Ok<'/api/tasks/list', 'get'>` 太难读，在这里起个名字。
// 名字与后端的概念对齐，不另发明一套

export type TaskView = Ok<'/api/tasks/list', 'get'>['tasks'][number]
export type TaskSnapshot = Ok<'/api/tasks', 'get'>
export type PreviewResult = Ok<'/api/preview', 'post'>
export type SettingsPayload = Ok<'/api/settings', 'get'>
export type SettingItem = SettingsPayload['items'][number]
export type SettingChoices = Ok<'/api/settings/choices', 'get'>
export type LoginStatus = Ok<'/api/login/status', 'get'>
export type SessionInfo = Ok<'/api/auth/session', 'get'>
export type FileEntry = Ok<'/api/files/list', 'get'>['entries'][number]
export type BilibiliStatus = Ok<'/api/login/status', 'get'>

// 解析结果是这份文件里**唯一**手写的结构，理由在后端 `web/schemas.py` 里写了：
// 树是递归的，叶子上的 `episode` 又是 TaskInfo 那套自由字典，硬套模型只会得到一堆
// Any。其余接口一律走生成的类型 —— 手写的迟早与后端对不上，而 TypeScript 会信以为真。
//
// 与后端 `parse/session.py` 的 `serialize_node()` 对齐，改那边就要改这里
export interface ParseNode {
  /**
   * 前端派发的位置路径（"0"、"0.1"），**后端不发这个字段**
   *
   * 后端的 episode_id 同一个视频的所有分P 共享，拿来当行标识会让分P 互相干扰；
   * 位置路径天然唯一。由 parseStore 的 indexTree 在加载时写上
   */
  id?: string
  title: string
  number: string | number
  badge: string
  cover: string
  duration: number
  /** 发布 / 收藏 / 观看时间。按来源只有其中一个有值，列表里合成一列显示 */
  pubtime?: number
  favtime?: number
  viewtime?: number
  /** 位标志的原始值，与桌面版 Attribute 对齐 */
  attribute: number
  /** 位标志摊平后的名字，前端靠它分支而不是自己解位 */
  attributes: string[]
  /** 只是分组用的节点，本身不可下载 */
  is_node: boolean
  checked: boolean
  children: ParseNode[]
  /** 只有叶子有。创建下载任务时原样回传，不必自己拼 */
  episode?: Record<string, unknown>
}

export interface ParseResult {
  title: string
  category: string
  parser_type: string
  url: string
  extra: Record<string, unknown>
  tree: ParseNode
  /** 链接指向的那一集的定位方式：按哪个字段找、找什么值 */
  current: { field: string; value: string | number } | null
}

// ---------------- WebUI 自身的会话 ----------------

export const auth = {
  session: () => get<SessionInfo>('/auth/session'),
  login: (username: string, password: string) =>
    post<Ok<'/api/auth/login', 'post'>>('/auth/login', { username, password }),
  logout: () => post<Ok<'/api/auth/logout', 'post'>>('/auth/logout'),
}

// ---------------- B 站账号 ----------------

export const login = {
  /** refresh 为真时会去问一次 nav 接口，顺带刷新 wbi 签名密钥 */
  status: (refresh = false) => get<LoginStatus>('/login/status', { refresh }),

  qrcode: () => post<Ok<'/api/login/qrcode', 'post'>>('/login/qrcode'),
  pollQrcode: (key: string) =>
    get<Ok<'/api/login/qrcode/poll', 'get'>>('/login/qrcode/poll', { key }),

  withCookie: (text: string) => post<Ok<'/api/login/cookie', 'post'>>('/login/cookie', { text }),

  smsRegions: () => get<Ok<'/api/login/sms/regions', 'get'>>('/login/sms/regions'),
  smsCaptcha: () => post<Ok<'/api/login/sms/captcha', 'post'>>('/login/sms/captcha'),
  smsSend: (payload: Body<'/api/login/sms/send', 'post'>) =>
    post<Ok<'/api/login/sms/send', 'post'>>('/login/sms/send', payload),
  smsVerify: (payload: Body<'/api/login/sms/verify', 'post'>) =>
    post<Ok<'/api/login/sms/verify', 'post'>>('/login/sms/verify', payload),

  logout: () => post<Ok<'/api/login/logout', 'post'>>('/login/logout'),
}

// ---------------- 解析与预览 ----------------

export const parse = {
  url: (url: string, pn = 1, signal?: AbortSignal) =>
    post<ParseResult>('/parse', { url, pn }, undefined, signal),

  /** 从解析树里摘出待下载的剧集。规则（树节点不算）只在后端有一份 */
  episodes: (tree: ParseNode, onlyChecked = true) =>
    post<Ok<'/api/parse/episodes', 'post'>>('/parse/episodes', tree, {
      only_checked: onlyChecked,
    }),
}

export const preview = {
  /** 候选按顺序尝试，首选没权限时后端会自动换下一个并置 from_fallback */
  media: (candidates: Record<string, unknown>[], signal?: AbortSignal) =>
    post<PreviewResult>('/preview', { candidates }, undefined, signal),
}

// ---------------- 任务 ----------------

export const tasks = {
  /** 全量快照。`cursor` 拿去连 WebSocket，否则快照与增量之间会漏事件 */
  snapshot: (limit?: number) => get<TaskSnapshot>('/tasks', { limit }),

  list: (
    options: { completed?: boolean; sortBy?: string; ascending?: boolean; limit?: number } = {},
  ) =>
    get<Ok<'/api/tasks/list', 'get'>>('/tasks/list', {
      completed: options.completed,
      sort_by: options.sortBy,
      ascending: options.ascending,
      limit: options.limit,
    }),

  count: () => get<Ok<'/api/tasks/count', 'get'>>('/tasks/count'),

  /** 这批条目里哪些已经下载过。返回的布尔列表与传进去的 episodes 一一对应、顺序一致 */
  duplicates: (episodes: Record<string, unknown>[]) =>
    post<Ok<'/api/tasks/duplicates', 'post'>>('/tasks/duplicates', { episodes }),

  create: (episodes: Record<string, unknown>[], options?: Record<string, unknown>) =>
    post<Ok<'/api/tasks', 'post'>>('/tasks', { episodes, options }),

  remove: (taskIds: string[], completed = false) =>
    post<Ok<'/api/tasks/delete', 'post'>>('/tasks/delete', { task_ids: taskIds }, { completed }),

  retry: (taskIds: string[]) =>
    post<Ok<'/api/tasks/retry', 'post'>>('/tasks/retry', { task_ids: taskIds }),

  pause: (taskIds: string[]) =>
    post<Ok<'/api/tasks/pause', 'post'>>('/tasks/pause', { task_ids: taskIds }),

  resume: (taskIds: string[]) =>
    post<Ok<'/api/tasks/resume', 'post'>>('/tasks/resume', { task_ids: taskIds }),
}

// ---------------- 配置与系统 ----------------

export const settings = {
  read: () => get<SettingsPayload>('/settings'),

  /** 结构化项的候选值（画质 / 音质 / 编码 / 字幕语言）。这些表只有 core 里那一份 */
  choices: () => get<SettingChoices>('/settings/choices'),
  /** 一项不合法则整批拒绝，返回里是纠正后的值（后端语义是纠正而非拒绝） */
  write: (values: Record<string, unknown>) =>
    post<Ok<'/api/settings', 'post'>>('/settings', { values }),
}

export const system = {
  status: () => get<Ok<'/api/status', 'get'>>('/status'),
  aria2: () => get<Ok<'/api/aria2/status', 'get'>>('/aria2/status'),
}

export const files = {
  roots: () => get<Ok<'/api/files/roots', 'get'>>('/files/roots'),
  list: (path: string, dirsOnly = false) =>
    get<Ok<'/api/files/list', 'get'>>('/files/list', { path, dirs_only: dirsOnly }),
  mkdir: (path: string, name: string) =>
    post<Ok<'/api/files/mkdir', 'post'>>('/files/mkdir', { path, name }),
}

export { ApiError, setUnauthorizedHandler } from './client'
