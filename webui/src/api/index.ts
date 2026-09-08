// 按域分组的接口调用
//
// 每个函数的入参与返回都从 `schema.d.ts` 推出来，**没有一处手写的结构**。
// 后端改了字段，这里会直接编译不过 —— 那正是要的效果（S3-12 加 `--check` 也是这个目的）。

import { get, post, del } from './client'
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
export type NamingRulePreviewResult = Ok<'/api/settings/naming-rule/preview', 'post'>
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
  /**
   * 发布 / 收藏 / 观看时间，秒级时间戳
   *
   * **不要假设「只有一个有值」** —— 收藏夹的条目发布时间与收藏时间都有。
   * 列表那一列该显示哪个，看下面的 dyn_time
   */
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
  /**
   * 这一列该显示的时间
   *
   * **由后端按 Attribute 位挑好**（收藏夹看收藏时间、历史记录看观看时间、
   * 其余看发布时间），前端不要自己在三个里面挑 —— 收藏夹的条目两个时间都有值
   */
  dyn_time?: number
  /** 只有叶子有。创建下载任务时原样回传，不必自己拼 */
  episode?: Record<string, unknown>
}

export interface ParseResult {
  title: string
  category: string
  /**
   * 时间列这一次显示的是哪一个：`pubtime` / `favtime` / `viewtime`
   *
   * 后端按类别挑好（与桌面版表头同一个函数），前端拿它去查列名 ——
   * 自己在前端按 category 判一遍的话，两边迟早对不上而且都不报错
   */
  time_column: string
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
  /**
   * 解析一个链接
   *
   * `keyword` 只对接口本身支持搜索的类型有效（个人空间、收藏夹、历史记录、稍后再看）。
   * 后端会把它写回链接 —— 翻页与解析历史因此都直接复用这条链接，不必再维护搜索状态
   */
  url: (url: string, pn = 1, keyword?: string, signal?: AbortSignal) =>
    post<ParseResult>('/parse', { url, pn, keyword }, undefined, signal),

  history: {
    list: () => get<Ok<'/api/parse/history', 'get'>>('/parse/history'),
    remove: (historyId: string) =>
      del<Ok<'/api/parse/history/{history_id}', 'delete'>>(
        `/parse/history/${encodeURIComponent(historyId)}`,
      ),
    clear: () => del<Ok<'/api/parse/history', 'delete'>>('/parse/history'),
  },

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
  /** 问版本服务有没有新版本。checked 为 false 表示这次没问成，看 error */
  checkUpdate: () => get<Ok<'/api/update', 'get'>>('/update'),

  read: () => get<SettingsPayload>('/settings'),

  /** 结构化项的候选值（画质 / 音质 / 编码 / 字幕语言 / 字幕对齐）。这些表只有 core 里那一份 */
  choices: () => get<SettingChoices>('/settings/choices'),

  /** 服务端装了哪些字体。ASS 在服务端生成，要的是那台机器上的字体 */
  fonts: () => get<Ok<'/api/settings/fonts', 'get'>>('/settings/fonts'),

  namingRuleTypes: () =>
    get<Ok<'/api/settings/naming-rule/types', 'get'>>('/settings/naming-rule/types'),

  namingRuleVariables: (type: number) =>
    get<Ok<'/api/settings/naming-rule/variables', 'get'>>('/settings/naming-rule/variables', {
      type,
    }),

  /** 校验一条规则并套上示例数据。非法的规则也返回 200，valid 为假 */
  namingRulePreview: (type: number, rule: string) =>
    post<Ok<'/api/settings/naming-rule/preview', 'post'>>('/settings/naming-rule/preview', {
      type,
      rule,
    }),
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
