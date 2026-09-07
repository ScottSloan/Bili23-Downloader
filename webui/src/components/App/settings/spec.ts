// 设置页显示哪些项、怎么分组、用什么控件
//
// ## 为什么要有这份清单
//
// `/api/settings` 会下发 91 个配置项。**不能照单全铺**：
//
// - 一部分是桌面窗口专用的（置顶、关窗行为、静默启动、Mica 效果、记住窗口位置），
//   浏览器里根本没有对应的东西，铺出来只会让人以为设了会生效
// - 一部分是一次性标记（各种 `*_dialog_shown`）、或程序自己维护的状态
//   （`config_version`、`is_login`、列表排序方式）
// - 一部分是结构复杂的表（弹幕样式、命名规则、CDN 列表、画质优先级），
//   要各自的编辑器才能改，不是一行卡片放得下的
//
// 所以这里挑，且**只挑，不重复声明类型**：控件类型、取值范围、默认值、是否需要重启
// 一律来自后端下发的 schema。在这里再写一遍 min/max 就等于维护第二份真相，
// 后端一改这边就悄悄对不上了。
//
// ## 分组顺序对着桌面版的设置界面
//
// 见 `src/gui/interface/setting.py`：Interface / Behavior / Download /
// Additional / Advanced。文案也照抄那边的 `self.tr(...)`，好让两边说的是同一件事。

/** 控件类型。不指定则按后端下发的 `type` 推断 */
export type ControlKind = 'switch' | 'combo' | 'spin' | 'text' | 'password' | 'path' | 'dialog'

/**
 * 结构化配置项的专用编辑器
 *
 * 这些项是列表或字典，一行卡片放不下，各自需要一个对话框。
 * 卡片上只放一个「自定义…」按钮加一句摘要 —— 与桌面版一致
 */
export type DialogKind =
  'priority' | 'subtitleLanguage' | 'browseRoots' | 'danmakuStyle' | 'subtitleStyle' | 'namingRule'

/** 启用条件：另一项为真，或等于某个值 */
export interface Condition {
  attr: string
  /** 不给则按「为真」判断 */
  equals?: string | number | boolean
}

export interface SettingSpec {
  /** 后端的 attr。找不到这一项时整张卡片跳过，不报错 —— 后端可能是旧版本 */
  attr: string
  kind?: ControlKind
  /** 缩进并在条件不满足时置灰 */
  enabledWhen?: Condition
  /** kind 为 dialog 时，用哪个编辑器 */
  dialog?: DialogKind
  /**
   * priority 编辑器的候选来自 `/api/settings/choices` 的哪一组
   *
   * 三个优先级项共用同一个对话框，靠这个字段区分候选表
   */
  choices?: 'video_quality' | 'audio_quality' | 'video_codec' | 'subtitle_language'
  /** 单位后缀，显示在数字框右侧 */
  suffix?: string
  step?: number
  decimals?: number
  /** 有说明文字的项在 i18n 里配 `settings.desc.<attr>`，这里标一下要不要取 */
  described?: boolean
  /**
   * 改完是否要重启后端。**不给则沿用后端下发的 `restart`**
   *
   * 那个标记是**桌面版的语义**，两边并不总是一致：
   *
   * - `language` 在后端标着要重启（Qt 得重新加载 .qm），但浏览器里 setLocale
   *   是立刻生效的 —— 照搬会显示一条假的提示
   * - `webui_port` / `aria2_rpc_port` 后端没标，可它们显然要重启才换得了监听端口
   *
   * 所以这一项按 WebUI 的实际情况覆盖，只有两边确实一致的才留空
   */
  restart?: boolean
}

export interface SettingGroupSpec {
  /** i18n 键：`settings.group.<key>` */
  key: string
  items: SettingSpec[]
}

/**
 * 界面组是特殊的：主题与主题色只存在浏览器本地（D14 各存各的），
 * 不走 `/api/settings`，所以由 SettingsView 单独渲染，不在这份清单里。
 * 只有语言是共用配置，放这儿
 */
export const INTERFACE_ITEMS: SettingSpec[] = [
  // 后端标着要重启（Qt 要重载 .qm），Web 端切完立刻生效
  { attr: 'language', described: true, restart: false },
]

export const SETTING_GROUPS: SettingGroupSpec[] = [
  {
    key: 'download',
    items: [
      { attr: 'download_path', kind: 'path', described: true },
      { attr: 'download_thread', suffix: '', described: true },
      { attr: 'download_parallel', described: true },
      { attr: 'speed_limit_enabled', described: true },
      {
        attr: 'speed_limit_rate',
        suffix: 'MB/s',
        step: 1,
        decimals: 1,
        enabledWhen: { attr: 'speed_limit_enabled' },
      },
      { attr: 'video_container', described: true },
      { attr: 'm4a_to_mp3', described: true },

      {
        attr: 'video_quality_priority',
        kind: 'dialog',
        dialog: 'priority',
        choices: 'video_quality',
        described: true,
      },
      {
        attr: 'audio_quality_priority',
        kind: 'dialog',
        dialog: 'priority',
        choices: 'audio_quality',
        described: true,
      },
      {
        attr: 'video_codec_priority',
        kind: 'dialog',
        dialog: 'priority',
        choices: 'video_codec',
        described: true,
      },
    ],
  },

  {
    key: 'behavior',
    items: [
      { attr: 'show_download_options_dialog', described: true },
      { attr: 'duplicate_download_resolution', described: true },
      { attr: 'file_conflict_resolution', described: true },
    ],
  },

  {
    key: 'additional',
    items: [
      { attr: 'download_danmaku' },
      { attr: 'danmaku_type', enabledWhen: { attr: 'download_danmaku' } },
      {
        attr: 'danmaku_style',
        kind: 'dialog',
        dialog: 'danmakuStyle',
        described: true,
        enabledWhen: { attr: 'download_danmaku' },
      },
      { attr: 'embed_danmaku', described: true, enabledWhen: { attr: 'download_danmaku' } },
      {
        attr: 'delete_danmaku_after_embed',
        described: true,
        enabledWhen: { attr: 'embed_danmaku' },
      },

      { attr: 'download_subtitle' },
      { attr: 'subtitle_type', enabledWhen: { attr: 'download_subtitle' } },
      {
        attr: 'subtitle_style',
        kind: 'dialog',
        dialog: 'subtitleStyle',
        described: true,
        enabledWhen: { attr: 'download_subtitle' },
      },
      {
        attr: 'subtitle_language',
        kind: 'dialog',
        dialog: 'subtitleLanguage',
        choices: 'subtitle_language',
        described: true,
        enabledWhen: { attr: 'download_subtitle' },
      },
      { attr: 'embed_subtitle', described: true, enabledWhen: { attr: 'download_subtitle' } },
      {
        attr: 'delete_subtitle_after_embed',
        described: true,
        enabledWhen: { attr: 'embed_subtitle' },
      },

      { attr: 'download_cover' },
      { attr: 'cover_type', enabledWhen: { attr: 'download_cover' } },
      { attr: 'attach_cover', described: true, enabledWhen: { attr: 'download_cover' } },
      {
        attr: 'delete_cover_after_attach',
        described: true,
        enabledWhen: { attr: 'attach_cover' },
      },

      { attr: 'embed_chapter', described: true },

      { attr: 'download_metadata' },
      { attr: 'metadata_type', enabledWhen: { attr: 'download_metadata' } },
    ],
  },

  {
    key: 'naming',
    items: [{ attr: 'naming_rule_list', kind: 'dialog', dialog: 'namingRule', described: true }],
  },

  {
    key: 'advanced',
    items: [
      { attr: 'prefer_cdn_server_provider', described: true },
      { attr: 'area', described: true },

      { attr: 'ffmpeg_source', described: true },
      {
        attr: 'custom_ffmpeg_path',
        kind: 'text',
        enabledWhen: { attr: 'ffmpeg_source', equals: 'custom' },
      },

      { attr: 'proxy_mode', described: true },
      { attr: 'proxy_server', enabledWhen: { attr: 'proxy_mode', equals: 'manual' } },
      { attr: 'proxy_port', enabledWhen: { attr: 'proxy_mode', equals: 'manual' } },
      { attr: 'proxy_uname', enabledWhen: { attr: 'proxy_mode', equals: 'manual' } },
      {
        attr: 'proxy_password',
        kind: 'password',
        enabledWhen: { attr: 'proxy_mode', equals: 'manual' },
      },

      { attr: 'user_agent', described: true },
    ],
  },

  {
    key: 'aria2',
    items: [
      { attr: 'aria2_managed', described: true, restart: true },
      { attr: 'aria2_path', kind: 'text', described: true, restart: true },
      { attr: 'aria2_rpc_host', described: true, restart: true },
      { attr: 'aria2_rpc_port', restart: true },
    ],
  },

  {
    key: 'webui',
    items: [
      { attr: 'webui_host', described: true, restart: true },
      { attr: 'webui_port', restart: true },
      { attr: 'webui_username', described: true },
      { attr: 'webui_session_hours', suffix: 'h', described: true },
      { attr: 'webui_browse_roots', kind: 'dialog', dialog: 'browseRoots', described: true },
    ],
  },
]

/**
 * attr → 清单项，给「依赖要一路往上看」用
 *
 * `enabledWhen` 只判一层是不够的：「嵌入后删除字幕文件」依赖「嵌入字幕」，而后者又
 * 依赖「下载字幕」。只看一层的话，关掉「下载字幕」之后「嵌入字幕」灰了、**但它的值
 * 仍是 true**，于是孙子项还亮着，用户能去改一个根本不会生效的开关
 */
export const SPEC_BY_ATTR: Record<string, SettingSpec> = Object.fromEntries(
  [...INTERFACE_ITEMS, ...SETTING_GROUPS.flatMap((group) => group.items)].map((spec) => [
    spec.attr,
    spec,
  ]),
)

/**
 * 没放进设置页的东西，写在这里备查（省得下次又论证一遍）
 *
 * - **只有桌面链路才读的项**：`preallocate_file_space` 只作用于内置下载器，
 *   而 WebUI 下载走的是 aria2；`auto_select_mode` 与 `parse_history` 的读取点
 *   全在 `gui/interface/parse.py`，Web 端的解析页没有对应实现。
 *   这三项摆出来是**假的开关** —— 用户设了，什么也不会发生
 * - **窗口行为**（`stay_on_top` / `when_close_window` / `silent_start` /
 *   `remember_window_state` / `window_state` / `show_notification` /
 *   `monitor_clipboard` / `mica_effect` / `display_scaling`）：桌面窗口专用
 * - **一次性标记**（`*_dialog_shown` / `accepted_terms` / `skip_version` /
 *   `config_version` / `is_login`）：程序自己维护
 * - **列表排序**（`downloading_list_sort_*` / `completed_list_sort_*` /
 *   `parse_list_*`）：由各自列表的表头控制，不该在设置页里另开一份
 * - **MCP**（`mcp_*`）：跑在桌面进程里，WebUI 改了不会生效
 * - **更新检查**（`include_prerelease`）：桌面版的自动更新，Docker 部署下不适用
 * - **还没有编辑器的结构化项**：`cn_cdn_server_list` / `ov_cdn_server_list`
 *   （`prefer_cdn_server_provider` 开关已覆盖多数场景，自定义 CDN 属于排障手段）、
 *   `auto_select_conditions`（跟 `auto_select_mode` 一起，Web 端还没有对应实现）
 *
 * `numbering_type` 单独说一句：它的 FROM_SPECIFIED 档要配合起始序号，而那是个
 * **进程级的运行时游标**（见 PROGRESS.md 待解决第 2 条），WebUI 是另一个进程、
 * 另一套并发模型，在那条改造做完之前不要在这里开放它
 */
export const OMITTED = true
