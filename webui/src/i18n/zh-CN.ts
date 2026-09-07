// 简体中文
//
// 与 GUI 共有的串直接取自 src/res/i18n/bili23.zh_CN.ts，措辞保持一致。
// 缺失的键会回落到 en.js 的英文源串。

export default {
  nav: {
    parse: '解析',
    download: '下载',
    settings: '设置',
  },

  parse: {
    placeholder: '链接 / av / BV / ep / ss / md / 收藏夹 / 个人空间',
    submit: '解析',
    submitting: '解析中',
    empty: '解析结果会显示在这里。',
    summary: '{category}（共 {total} 项，已选 {checked} 项）',
    mediaUnavailable: '媒体信息不可用（{reason}），暂时无法下载',
    download: '下载选中项',
    nothingChecked: '没有勾选任何内容。',
    created: '已创建 {count} 个任务（共勾选 {requested} 项）。',
    createdNone: '没有创建任务，可能都已经在队列里了。',
    tagDownloaded: '已下载',
    tagNeedsReparse: '需二次解析',
  },

  user: {
    signedOut: '未登录',
    avatarAlt: '用户头像',
  },

  settings: {
    title: '设置',
    loading: '正在读取设置…',
    saving: '正在保存…',
    saveFailed: '保存失败：{message}',
    restartBadge: '需重启',
    restartNotice: '以下设置需要重启后端后生效：{items}',
    localOnly: '仅保存在当前浏览器',
    customize: '自定义…',

    dialog: {
      save: '保存',
      cancel: '取消',
    },

    priority: {
      hint: '越靠前越优先。视频没有该档位时，依次尝试下一个。',
      summary: '优先 {first}',
      moveUp: '上移',
      moveDown: '下移',
    },

    subtitleLanguage: {
      title: '自定义字幕语言',
      all: '下载全部可用字幕',
      specified: '仅下载选中的字幕',
      search: '按名称或语言代码搜索',
      empty: '没有匹配的语言。',
      selected: '已选 {count} 种',
      summaryAll: '全部可用字幕',
      summarySome: '已选 {count} 种',
    },

    browseRoots: {
      title: '可浏览的目录',
      hint: '填的是运行后端那台机器上的路径，不是本机的。只能手输 —— 还没成为根目录的地方，浏览接口本来就不让看。',
      placeholder: '/downloads',
      add: '添加',
      remove: '移除',
      empty: '没有额外目录，只能浏览下载目录。',
      summary: '{count} 个目录',
      summaryEmpty: '仅下载目录',
    },

    theme: {
      label: '主题',
      description: '选择应用程序主题',
      light: '浅色',
      dark: '深色',
      system: '系统默认',
    },

    accent: {
      label: '强调色',
      description: '自定义应用程序中使用的强调色',
      reset: '恢复默认',
    },

    group: {
      interface: '界面',
      download: '下载',
      behavior: '行为',
      additional: '弹幕、字幕、封面、章节和元数据',
      advanced: '高级',
      aria2: 'aria2',
      webui: 'WebUI',
    },

    label: {
      language: '语言',

      download_path: '下载路径',
      download_thread: '多线程数',
      download_parallel: '并行下载数',
      speed_limit_enabled: '下载速度限制',
      speed_limit_rate: '限速值',
      video_container: '输出容器格式',
      m4a_to_mp3: '将 M4A 转换为 MP3',

      video_quality_priority: '视频清晰度优先级',
      audio_quality_priority: '音质优先级',
      video_codec_priority: '编码优先级',
      subtitle_language: '字幕语言',
      webui_browse_roots: '可浏览的目录',

      show_download_options_dialog: '下载时显示选项对话框',
      duplicate_download_resolution: '重复下载处理',
      file_conflict_resolution: '同名文件处理',

      download_danmaku: '下载弹幕',
      danmaku_type: '弹幕格式',
      embed_danmaku: '嵌入弹幕',
      delete_danmaku_after_embed: '嵌入后删除弹幕文件',
      download_subtitle: '下载字幕',
      subtitle_type: '字幕格式',
      embed_subtitle: '嵌入字幕',
      delete_subtitle_after_embed: '嵌入后删除字幕文件',
      download_cover: '下载封面',
      cover_type: '封面格式',
      attach_cover: '嵌入封面',
      delete_cover_after_attach: '嵌入后删除封面',
      embed_chapter: '嵌入章节信息',
      download_metadata: '下载元数据',
      metadata_type: '元数据格式',

      prefer_cdn_server_provider: '优先使用服务商 CDN',
      area: '所在地区',
      ffmpeg_source: 'FFmpeg 来源',
      custom_ffmpeg_path: '自定义 FFmpeg 路径',
      proxy_mode: '代理模式',
      proxy_server: '代理服务器',
      proxy_port: '代理端口',
      proxy_uname: '代理用户名',
      proxy_password: '代理密码',
      user_agent: '自定义 User-Agent',

      aria2_managed: '由 Bili23 托管',
      aria2_path: 'aria2c 路径',
      aria2_rpc_host: 'RPC 地址',
      aria2_rpc_port: 'RPC 端口',

      webui_host: '监听地址',
      webui_port: '端口',
      webui_username: '用户名',
      webui_session_hours: '登录有效期',
    },

    desc: {
      language: '选择应用程序的显示语言',

      download_path: '下载文件的保存位置。已在队列中的任务仍使用创建时的目录。',
      download_thread: '调整单个任务使用的线程数，默认为 4',
      download_parallel: '调整同时下载的任务数，默认为 1',
      speed_limit_enabled: '限制所有任务的总下载速度',
      video_container: '选择最终输出视频文件的容器格式',
      m4a_to_mp3: '仅在下载纯音频流时有效',

      video_quality_priority: '视频有多个清晰度可选时，优先选择哪一个',
      audio_quality_priority: '有多种音质可选时，优先选择哪一个',
      video_codec_priority: '有多种编码可选时，优先选择哪一个',
      subtitle_language: '下载全部字幕，还是只下你指定的语言',
      webui_browse_roots: '「选择文件夹」允许浏览的范围。留空则只能浏览下载目录。',

      show_download_options_dialog: '在开始下载前弹出对话框，以便自定义本次下载设置',
      duplicate_download_resolution:
        '选择检测到重复下载时的操作。WebUI 没有可询问的对象，因此设为「总是询问」时会直接跳过。',
      file_conflict_resolution: '选择当目标位置已存在同名文件时的操作',

      embed_danmaku: '将弹幕作为字幕轨嵌入到视频文件中，仅在弹幕格式为 ASS 且输出容器为 MKV 时可用',
      delete_danmaku_after_embed: '将弹幕嵌入视频文件后删除原弹幕文件',
      embed_subtitle:
        '将字幕作为字幕轨嵌入到视频文件中，仅在字幕格式为 ASS 且输出容器为 MKV 时可用',
      delete_subtitle_after_embed: '将字幕嵌入视频文件后删除原字幕文件',
      attach_cover: '将下载的封面嵌入到视频文件中',
      delete_cover_after_attach: '将封面嵌入视频文件后删除原封面文件',
      embed_chapter: '将视频的分段章节写入视频文件，仅在合并视频和音频时生效',

      prefer_cdn_server_provider: '优先使用服务器商提供的 CDN，提高下载稳定性',
      area: '选择实际位置，以自动匹配更合适的 CDN 服务器并提升下载速度',
      ffmpeg_source: '选择要使用的 FFmpeg 可执行文件',
      proxy_mode: '选择用于解析和下载的代理',
      user_agent: '为网络请求设置自定义 User-Agent 字符串',

      aria2_managed: '随 WebUI 一起启动和停止 aria2。关闭后将连接你自己运行的 aria2。',
      aria2_path: '留空则在系统环境变量中查找 aria2c',
      aria2_rpc_host: 'aria2 监听 RPC 的地址',

      webui_host: '填 127.0.0.1 只接受本机连接，填 0.0.0.0 则接受来自网络的连接',
      webui_username: '登录本页面所用的账号',
      webui_session_hours: '一次登录的有效时长',
    },

    option: {
      language: {
        zh_CN: '简体中文',
        zh_TW: '繁體中文',
        en_US: 'English',
        Auto: '系统默认',
      },
      area: {
        cn: '中国大陆',
        ov: '中国大陆以外地区（包括香港、澳门和台湾）',
      },
      ffmpeg_source: {
        bundled: '程序附带',
        system: '系统环境变量',
        custom: '自定义路径',
      },
      proxy_mode: {
        disabled: '不使用代理',
        system: '使用系统代理',
        manual: '手动设置',
      },
      duplicate_download_resolution: {
        0: '继续下载',
        1: '跳过',
        2: '总是询问',
      },
      file_conflict_resolution: {
        1: '自动重命名',
        2: '覆盖文件',
      },
    },

    picker: {
      title: '选择文件夹',
      locations: '位置',
      parent: '上一级',
      newFolder: '新建文件夹',
      newFolderPlaceholder: '文件夹名称',
      create: '创建',
      empty: '此文件夹下没有子文件夹。',
      truncated: '条目过多，仅显示前 {count} 项。',
      choose: '使用此文件夹',
      cancel: '取消',
      failed: '无法打开此文件夹：{message}',
      noRoots: '没有配置可浏览的目录。请在 config.json 中设置 webui_browse_roots。',
    },
  },

  column: {
    number: '序号',
    title: '标题名称',
    badge: '备注',
    duration: '时长',
    dyn_time: '发布时间 / 收藏时间 / 上次观看时间',
    pubtime: '发布时间',
    favtime: '收藏时间',
    viewtime: '上次观看时间',
  },

  download: {
    title: '下载 {count} 项',
    loading: '正在获取媒体信息…',
    fallback: '首选的视频无法获取媒体信息，以下清晰度来自「{title}」。',
    videoQuality: '视频清晰度',
    videoCodec: '视频编码',
    audioQuality: '音质',
    extras: '同时下载',
    danmaku: '弹幕',
    subtitle: '字幕',
    cover: '封面',
    metadata: '元数据',
    cancel: '取消',
    confirm: '开始下载',
    submitting: '创建中',
  },

  task: {
    summary: '{total} 个任务，{active} 个进行中',
    offline: '实时更新已断开',
    empty: '暂无下载任务。',
    completedSection: '已完成（{count}）',
    pause: '暂停',
    resume: '继续',
    retry: '重新下载',
    remove: '删除',
    status: {
      queued: '等待下载',
      parsing: '解析中',
      downloading: '下载中',
      paused: '已暂停',
      completed: '已完成',
      ffmpeg_queued: '等待处理',
      merging: '合并中',
      converting: '转换中',
      additional_processing: '获取附加内容',
      failed: '下载失败',
      ffmpeg_failed: '处理失败',
      unknown: '未知',
    },
  },

  auth: {
    title: '登录',
    hint: '口令在首次启动时打印到控制台，只显示一次，且不会写入日志文件。',
    username: '用户名',
    password: '口令',
    submit: '登录',
    submitting: '登录中',
    failed: '用户名或口令不正确。',
    expired: '登录已过期，请重新登录。',
    signOut: '退出 WebUI',
  },

  error: {
    backendUnreachable: '无法连接到后端，请先运行：python src/main.py --web-ui',
    requestFailed: '请求失败（HTTP {status}）',
  },
}
