// 英文源串 —— 与 GUI 一致，英文是源语言，其余语言由译文文件覆盖（D12）
//
// 措辞尽量照抄 GUI 里对应的 self.tr(...) / Translator，这样译文可以直接从
// src/res/i18n/bili23.*.ts 里取，不用重新斟酌。但**不共用**那套表：
// 那是 Qt 的翻译体系，服务端不该被拖进来。

export default {
  nav: {
    parse: 'Parser',
    download: 'Download',
    settings: 'Settings',
  },

  // 气泡提示的标题。桌面版每条 InfoBar 都有标题 + 正文两段，标题写「发生了什么」
  toast: {
    parseFailed: 'Parse Failed',
    saveFailed: 'Save Failed',
    loadFailed: 'Load Failed',
    done: 'Done',
    notice: 'Notice',
  },

  parse: {
    placeholder: 'Link / av / BV / ep / ss / md / Favorites / Profile',
    submit: 'Parse',
    submitting: 'Parsing',
    empty: 'Parsed results will appear here.',
    // GUI 的原串是 "{category_name} ({total_count} total)"，Web 端多显示一个已选数
    summary: '{category} ({total} total, {checked} selected)',
    mediaUnavailable:
      'Media information is unavailable ({reason}), downloads cannot be created yet.',
    download: 'Download selected',
    nothingChecked: 'Nothing selected.',
    created: 'Created {count} of {requested} task(s).',
    createdNone: 'No task was created — they may already exist in the queue.',
    tagDownloaded: 'Downloaded',
    tagNeedsReparse: 'Needs re-parsing',

    // 工具栏那四个按钮。措辞抄桌面版 gui/interface/parse.py 的 setToolTip
    toolbar: {
      search: 'Search',
      history: 'Parsing History',
      batchSelect: 'Batch Select',
      downloadOptions: 'Download Options',
    },

    search: {
      title: 'Search',
      placeholder: 'Enter keywords to search',
      scope: 'Search scope',
      filterPage: 'Filter the current page only',
      searchAll: 'Search all pages',
      paginationTip:
        'Only the current page can be filtered. To search the full list, parse all pages first.',
      confirm: 'Search',
      matches: 'Matched {count} item(s)',
    },

    batchSelect: {
      title: 'Batch Selection',
      placeholder: 'Enter line numbers (e.g. 1,3,5-10)',
      guide: 'Separate numbers with commas, and use a hyphen for ranges. Already checked items stay checked.',
      confirm: 'Select',
      count: '{count} line number(s) entered',
      empty: 'Please enter line numbers',
      invalid: 'Invalid line number',
      selected: 'Selected {count} item(s)',
    },

    history: {
      title: 'Parse History',
      limit: 'Only the latest {count} records are kept. Shared with the desktop app.',
      clear: 'Clear History',
      remove: 'Delete',
      close: 'Close',
      loading: 'Loading…',
      empty: 'No history yet.',
      no: 'No.',
      name: 'Title',
      type: 'Type',
      time: 'Parse Time',
      actions: 'Actions',
    },


    batchParse: {
      title: 'Batch Parse',
      placeholder: 'Paste video links here, one per line. Currently only av and BV links are supported.',
      count: 'Link Count: {count}',
      clear: 'Clear',
      autoAdd: 'Automatically add to download list after parsing each link',
      start: 'Start Parsing',
      stop: 'Stop',
      noLinks: 'Please paste video links in the text box.',
      invalid: 'Currently only av or BV links are supported.',
      progress: 'Parsing {done} / {total}…',
      done: 'Batch parse finished, {count} item(s) in the list',
      doneWithTasks: 'Batch parse finished, {count} task(s) created',
    },

  },

  user: {
    signedOut: 'Not signed in',
    avatarAlt: 'User avatar',
  },

  settings: {
    title: 'Settings',
    loading: 'Loading settings…',
    saving: 'Saving…',
    saveFailed: 'Could not save: {message}',
    restartBadge: 'Restart required',
    restartNotice: 'Restart the backend for these to take effect: {items}',
    localOnly: 'Stored in this browser only',
    customize: 'Customize…',

    dialog: {
      save: 'Save',
      cancel: 'Cancel',
    },

    priority: {
      hint: 'The topmost entry is preferred. If a video does not offer it, the next one is tried.',
      summary: 'Prefers {first}',
      moveUp: 'Move up',
      moveDown: 'Move down',
    },

    subtitleLanguage: {
      title: 'Customize Subtitle Languages',
      all: 'Download all available subtitles',
      specified: 'Download only selected subtitles',
      search: 'Search by name or code',
      empty: 'No language matches.',
      selected: '{count} selected',
      summaryAll: 'All available',
      summarySome: '{count} selected',
    },

    browseRoots: {
      title: 'Browsable Folders',
      hint: 'Paths on the machine running the backend, not on this device. Type the full path — folders that are not roots yet cannot be browsed to.',
      placeholder: '/downloads',
      add: 'Add',
      remove: 'Remove',
      empty: 'No extra folder. Only the download folder can be browsed.',
      summary: '{count} folder(s)',
      summaryEmpty: 'Download folder only',
    },

    theme: {
      label: 'Theme',
      description: 'Select the application theme',
      light: 'Light',
      dark: 'Dark',
      system: 'System default',
    },

    accent: {
      label: 'Accent Color',
      description: 'Customize the accent color used in the application',
      reset: 'Reset',
    },

    // 开关左边那两个字。桌面版的 SwitchSettingCard 一律带着它，
    // 译文取自 qfluentwidgets 自带的翻译（不是本项目的 .ts）
    switch: {
      on: 'On',
      off: 'Off',
    },

    group: {
      interface: 'Interface',
      download: 'Download',
      behavior: 'Behavior',
      additional: 'Danmaku, Subtitles, Cover, Chapters, and Metadata',
      advanced: 'Advanced',
      naming: 'File naming',
    },

    // 折叠卡片的标题与说明。文案抄自桌面版 gui/component/setting/card.py 的 self.tr(...)，
    // 好让两端说的是同一件事；aria2 与 WebUI 两张卡片桌面版没有，是这边自己写的
    card: {
      parsing: { title: 'Parsing Settings', desc: 'Configure how parsing behaves' },
      personalization: { title: 'Personalization', desc: 'Customize the app theme, colors, and visual effects' },
      concurrency: { title: 'Download Concurrency', desc: 'Adjust per-task threads, concurrent downloads, and speed limits' },
      priority: { title: 'Video, Audio, and Codec Priority', desc: 'Customize download priority settings' },
      downloadFormat: { title: 'Download Format', desc: 'Configure output format settings for downloaded files' },
      downloadHandling: { title: 'Download Handling', desc: 'Configure download prompts, duplicate handling, and file conflicts' },
      danmaku: { title: 'Danmaku Download Settings', desc: 'Adjust danmaku download settings' },
      subtitle: { title: 'Subtitle Download Settings', desc: 'Adjust subtitle download settings' },
      cover: { title: 'Cover Download Settings', desc: 'Adjust cover download settings' },
      chapter: { title: 'Chapter Settings', desc: 'Adjust chapter settings' },
      metadata: { title: 'Metadata Download Settings', desc: 'Adjust metadata download settings' },
      cdn: { title: 'CDN Settings', desc: 'Adjust CDN settings used for downloading' },
      ffmpeg: { title: 'FFmpeg Settings', desc: 'Configure FFmpeg used for merging and converting videos' },
      proxy: { title: 'Proxy Settings', desc: 'Adjust proxy server settings used for parsing and downloading' },
      aria2: { title: 'aria2 Settings', desc: 'Configure the aria2 downloader used by the WebUI' },
      webui: { title: 'WebUI Settings', desc: 'Configure the service address, sign-in, and browsable directories' },
    },

    label: {
      parse_history: 'Save Parse History',
      language: 'Language',

      download_path: 'Download Path',
      download_thread: 'Number of Threads',
      download_parallel: 'Number of Parallel Downloads',
      speed_limit_enabled: 'Speed Limit',
      speed_limit_rate: 'Speed Limit Rate',
      video_container: 'Output Container Format',
      m4a_to_mp3: 'Convert M4A to MP3',

      video_quality_priority: 'Video Quality Priority',
      audio_quality_priority: 'Audio Quality Priority',
      video_codec_priority: 'Codec Priority',
      subtitle_language: 'Subtitle Language',
      webui_browse_roots: 'Browsable Folders',

      show_download_options_dialog: 'Show Download Options Dialog',
      duplicate_download_resolution: 'Duplicate Download Resolution',
      file_conflict_resolution: 'File Conflict Resolution',

      download_danmaku: 'Download Danmaku',
      danmaku_type: 'Danmaku Format',
      embed_danmaku: 'Embed Danmaku',
      delete_danmaku_after_embed: 'Delete Danmaku After Embedding',
      download_subtitle: 'Download Subtitles',
      subtitle_type: 'Subtitle Format',
      embed_subtitle: 'Embed Subtitles',
      delete_subtitle_after_embed: 'Delete Subtitles After Embedding',
      download_cover: 'Download Cover',
      cover_type: 'Cover Format',
      attach_cover: 'Embed Cover',
      delete_cover_after_attach: 'Delete Cover After Embedding',
      embed_chapter: 'Embed Chapters',
      download_metadata: 'Download Metadata',
      metadata_type: 'Metadata Format',
      danmaku_style: 'Danmaku Style',
      subtitle_style: 'Subtitle Style',
      naming_rule_list: 'Naming Convention',

      prefer_cdn_server_provider: 'Prefer Service Provider CDN',
      area: 'Geographic Location',
      ffmpeg_source: 'FFmpeg Source',
      custom_ffmpeg_path: 'Custom FFmpeg Path',
      proxy_mode: 'Proxy Mode',
      proxy_server: 'Proxy Server',
      proxy_port: 'Proxy Port',
      proxy_uname: 'Proxy Username',
      proxy_password: 'Proxy Password',
      user_agent: 'Custom User-Agent',

      aria2_managed: 'Managed by Bili23',
      aria2_path: 'aria2c Path',
      aria2_rpc_host: 'RPC Host',
      aria2_rpc_port: 'RPC Port',

      webui_host: 'Listen Address',
      webui_port: 'Port',
      webui_username: 'Username',
      webui_session_hours: 'Session Lifetime',
    },

    desc: {
      parse_history: 'Save the history of parsed links. Shared with the desktop app.',
      language: 'Choose the display language of the application',

      download_path:
        'Where downloaded files are saved. Tasks already in the queue keep the folder they were created with.',
      download_thread: 'Adjust the number of threads used per task (default: 4)',
      download_parallel: 'Adjust the number of tasks downloaded simultaneously (default: 1)',
      speed_limit_enabled: 'Limit the combined download speed',
      video_container: 'Choose the container format for the final output video file',
      m4a_to_mp3:
        'Only applies when downloading audio-only streams. Disabled if video is also selected.',

      video_quality_priority: 'Which quality to prefer when a video offers several',
      audio_quality_priority: 'Which audio quality to prefer when several are available',
      video_codec_priority: 'Which codec to prefer when several are available',
      subtitle_language: 'Download all subtitles, or only the languages you pick',
      webui_browse_roots:
        'Where the folder picker is allowed to look. Leave empty to allow the download folder only.',

      show_download_options_dialog:
        'Show a dialog before starting the download to customize settings for this task',
      duplicate_download_resolution:
        'Choose the action when a duplicate download is detected. The WebUI has nobody to ask, so duplicates are skipped while this is set to Always ask.',
      file_conflict_resolution: 'Choose the action when a file with the same name already exists',

      embed_danmaku:
        'Embed danmaku into the video file as a subtitle track, only available when the format is ASS and the output container is MKV',
      delete_danmaku_after_embed:
        'Delete the original danmaku file after embedding it into the video file',
      embed_subtitle:
        'Embed subtitles into the video file as subtitle tracks, only available when the format is ASS and the output container is MKV',
      delete_subtitle_after_embed:
        'Delete the original subtitle files after embedding them into the video file',
      attach_cover: 'Embed the downloaded cover into the video file',
      delete_cover_after_attach:
        'Delete the original cover file after embedding it into the video file',
      danmaku_style: 'Only effective for ASS format danmaku',
      subtitle_style: 'Only effective for ASS format subtitles',
      naming_rule_list: 'Customize the naming convention for downloaded files',
      embed_chapter:
        'Embed the video chapters into the video file, only effective when merging video and audio',

      prefer_cdn_server_provider:
        'Prefer CDN provided by cloud service providers to improve download stability',
      area: 'Select your actual location to automatically match a more suitable CDN server and improve download speed',
      ffmpeg_source: 'Select the FFmpeg executable to use',
      proxy_mode: 'Select the proxy used for parsing and downloading',
      user_agent: 'Set a custom User-Agent string for network requests',

      aria2_managed:
        'Start and stop aria2 together with the WebUI. Turn this off to connect to an aria2 instance you run yourself.',
      aria2_path: 'Leave empty to look for aria2c on the system PATH',
      aria2_rpc_host: 'The address aria2 listens on for RPC',

      webui_host:
        'Use 127.0.0.1 to accept connections from this machine only, or 0.0.0.0 to accept them from the network',
      webui_username: 'The account used to sign in to this page',
      webui_session_hours: 'How long a sign-in stays valid',
    },

    // 枚举的选项名。文件格式（ass / mp4 / nfo…）不在这里 —— 它们直接大写显示，
    // 三种语言下都一样，列出来只是徒增 40 条要维护的串
    option: {
      language: {
        zh_CN: '简体中文',
        zh_TW: '繁體中文',
        en_US: 'English',
        Auto: 'System default',
      },
      area: {
        cn: 'Mainland China',
        ov: 'Outside Mainland China (Including Hong Kong, Macau, and Taiwan)',
      },
      ffmpeg_source: {
        bundled: 'Bundled (with app)',
        system: 'System PATH',
        custom: 'Custom path',
      },
      proxy_mode: {
        disabled: 'Do not use proxy',
        system: 'Use system proxy',
        manual: 'Manual configuration',
      },
      duplicate_download_resolution: {
        0: 'Continue',
        1: 'Skip',
        2: 'Always ask',
      },
      file_conflict_resolution: {
        1: 'Auto-rename',
        2: 'Overwrite',
      },
    },

    style: {
      danmakuTitle: 'Customize Danmaku Style',
      subtitleTitle: 'Customize Subtitle Style',
      hint: 'Only applies to the ASS format.',
      sectionFont: 'Font',
      sectionBorder: 'Outline and Shadow',
      sectionAdvanced: 'Layout',
      sectionColor: 'Colors',
      sectionMargin: 'Margins',
      sectionResolution: 'Resolution',
      fontName: 'Font Family',
      fontNamePlaceholder: 'Font name as installed on the server',
      fontSize: 'Font Size',
      bold: 'Bold',
      italic: 'Italic',
      underline: 'Underline',
      strike: 'Strikeout',
      outline: 'Outline (px)',
      shadow: 'Shadow (px)',
      display_area: 'Display Area (%)',
      opacity: 'Opacity (%)',
      scroll_duration: 'Scroll Duration (s)',
      static_duration: 'Static Duration (s)',
      minimum_gap: 'Minimum Horizontal Spacing (px)',
      color_primary: 'Primary Color',
      color_secondary: 'Secondary Color',
      color_border: 'Outline Color',
      color_shadow: 'Shadow Color',
      alpha: 'Alpha',
      margin_left: 'Left Margin (px)',
      margin_right: 'Right Margin (px)',
      margin_vertical: 'Vertical Margin (px)',
      alignment: 'Alignment',
      screen_width: 'Screen Width (px)',
      screen_height: 'Screen Height (px)',
    },

    namingRule: {
      title: 'Naming Rules',
      editTitle: 'Edit Naming Rule',
      summary: '{count} rule(s)',
      add: 'Add',
      edit: 'Edit',
      delete: 'Delete',
      done: 'Done',
      default: 'Default',
      name: 'Rule Name',
      type: 'Rule Type',
      rule: 'Naming Rule',
      setDefault: 'Set as default rule for this type',
      preview: 'Preview',
      previewResult: 'Folder: {folder} · File name: {filename}',
      previewFailed: 'Could not check this rule.',
      invalid: 'Invalid naming rule',
      nameRequired: 'Rule name cannot be empty',
      cannotDeleteDefault: 'Only non-default naming rules can be deleted.',
      preset: {
        DEFAULT_FOR_NORMAL: 'Preset: Single Video',
        DEFAULT_FOR_PART: 'Preset: Multi-part Series',
        DEFAULT_FOR_COLLECTION: 'Preset: Collection',
        DEFAULT_FOR_INTERACTIVE_VIDEO: 'Preset: Interactive Video',
        DEFAULT_FOR_BANGUMI: 'Preset: Film & TV',
        DEFAULT_FOR_CHEESE: 'Preset: Courses',
        DEFAULT_FOR_LESSON: 'Preset: Mall Courses',
        DEFAULT_FOR_FAVORITE: 'Preset: Favorites',
        DEFAULT_FOR_SPACE: 'Preset: Profile',
        DEFAULT_FOR_AUDIO: 'Preset: Music',
        DEFAULT_FOR_HISTORY: 'Preset: History',
        DEFAULT_FOR_WEEKLY: 'Preset: Weekly Picks',
        DEFAULT_FOR_WATCH_LATER: 'Preset: Watch Later',
      },
    },

    picker: {
      title: 'Choose folder',
      locations: 'Locations',
      parent: 'Up one level',
      newFolder: 'New folder',
      newFolderPlaceholder: 'Folder name',
      create: 'Create',
      empty: 'This folder has no subfolders.',
      truncated: 'Only the first {count} entries are shown.',
      choose: 'Use this folder',
      cancel: 'Cancel',
      failed: 'Cannot open this folder: {message}',
      noRoots:
        'No browsable folders are configured. Set webui_browse_roots in config.json to allow browsing.',
    },
  },

  // 后端下发的数据标签在这里翻译（D12：不与 Qt 那套共用）
  //
  // 服务端进程里没装 Qt 的翻译函数，`Translator` 返回的一律是英文源串 ——
  // 照搬的话，中文界面上会出现 `8K UHD`、`Single Video` 这种英文标签。
  //
  // 键是**后端给的稳定取值**（画质 id、规则类型编号），不是英文串：
  // 那些数字是 B 站的协议，比英文措辞稳定得多。
  //
  // 这里认不出的值会回落到后端给的 label —— B 站加一档新画质时，
  // 至少还能显示它的英文名，而不是一个裸数字。
  //
  // **字幕语言（158 条）不在这里**：那是 B 站自己的语言表，源数据只有中文名，
  // 桌面版也是直接显示它。翻一遍不现实，也没有第二份可抄
  media: {
    video_quality: {
      200: 'Auto (by priority)',
      127: '8K UHD',
      126: 'Dolby Vision',
      125: 'HDR True Color',
      122: '4K SDR Enhanced',
      120: '4K UHD',
      116: '1080P 60fps',
      112: '1080P High Bitrate',
      100: 'AI Upscale',
      80: '1080P',
      64: '720P',
      32: '480P',
      16: '360P',
    },

    audio_quality: {
      30300: 'Auto (by priority)',
      30251: 'Hi-Res Audio',
      30250: 'Dolby Atmos',
      30280: '192 kbps',
      30232: '132 kbps',
      30216: '64 kbps',
    },

    video_codec: {
      20: 'Auto (by priority)',
      7: 'AVC/H.264',
      12: 'HEVC/H.265',
      13: 'AV1',
    },

    subtitle_alignment: {
      1: 'Bottom Left',
      2: 'Bottom Center',
      3: 'Bottom Right',
      4: 'Middle Left',
      5: 'Middle Center',
      6: 'Middle Right',
      7: 'Top Left',
      8: 'Top Center',
      9: 'Top Right',
    },

    naming_type: {
      11: 'Single Video',
      12: 'Multi-part Series',
      13: 'Collection',
      14: 'Interactive Video',
      20: 'Film & TV',
      30: 'Courses',
      31: 'Mall Courses',
      40: 'Favorites',
      50: 'Profile',
      60: 'History',
      70: 'Watch Later',
      80: 'Weekly Picks',
      90: 'Music',
    },
  },

  // 键与后端 parse_list_column 的 attr_key 一一对应
  column: {
    number: 'No.',
    title: 'Title',
    badge: 'Notes',
    duration: 'Duration',
    dyn_time: 'Publish Time / Favorite Time / Last Watched',
    pubtime: 'Publish Time',
    favtime: 'Favorite Time',
    viewtime: 'Last Watched',
  },

  download: {
    title: 'Download {count} item(s)',
    loading: 'Fetching media information…',
    fallback:
      'Media information comes from another video ({title}) because the first choice is not accessible.',
    videoQuality: 'Video quality',
    videoCodec: 'Video codec',
    audioQuality: 'Audio quality',
    extras: 'Also download',
    danmaku: 'Danmaku',
    subtitle: 'Subtitles',
    cover: 'Cover',
    metadata: 'Metadata',
    cancel: 'Cancel',
    confirm: 'Start download',
    submitting: 'Creating',
  },

  task: {
    summary: '{active} downloading of {total}',
    offline: 'Live updates disconnected',
    empty: 'No download tasks yet.',
    completedSection: 'Completed ({count})',
    pause: 'Pause',
    resume: 'Resume',
    retry: 'Redownload',
    remove: 'Remove',
    status: {
      queued: 'Queued',
      parsing: 'Parsing',
      downloading: 'Downloading',
      paused: 'Paused',
      completed: 'Completed',
      ffmpeg_queued: 'Queued for FFmpeg',
      merging: 'Merging',
      converting: 'Converting',
      additional_processing: 'Fetching extras',
      failed: 'Download failed',
      ffmpeg_failed: 'FFmpeg failed',
      unknown: 'Unknown',
    },
  },

  auth: {
    title: 'Sign in',
    hint: 'The password was printed to the console on first launch. It is shown only once and is not written to the log file.',
    username: 'Username',
    password: 'Password',
    submit: 'Sign in',
    submitting: 'Signing in',
    failed: 'Incorrect username or password.',
    expired: 'Your session has expired. Please sign in again.',
    signOut: 'Sign out of the WebUI',
  },

  error: {
    // 后端固定错误的文案。**键是后端给的 code，不是它给的英文句子**
    //
    // 服务端进程里没装 Qt 的翻译函数（D12），后端写出来的 detail 一律是英文。
    // 这里按码查前端自己的译文，查不到才回落到 detail —— 那既包括后端加了新码
    // 而这里还没配，也包括 str(e) 那类透传（内容来自 B 站接口，前端翻不了）
    code: {
      NOT_AUTHENTICATED: 'Not signed in.',
      INVALID_CREDENTIALS: 'Incorrect username or password.',
      TOO_MANY_ATTEMPTS: 'Too many failed attempts. Try again later.',
      PARSE_BUSY: 'Too many parses running. Wait for one to finish.',
      TASK_NOT_FOUND: 'This task no longer exists.',
      NO_MATCHING_TASK: 'No matching task.',
      UNKNOWN_SORT_KEY: 'Unknown sort key.',
      NOT_A_DIRECTORY: 'Not a folder.',
      PARENT_NOT_A_DIRECTORY: 'The parent is not a folder.',
      PERMISSION_DENIED: 'Permission denied.',
      CANNOT_READ_DIRECTORY: 'Cannot read this folder.',
      CANNOT_CREATE_DIRECTORY: 'Cannot create the folder.',
      INVALID_FOLDER_NAME: 'Invalid folder name.',
      FOLDER_NAME_HAS_SEPARATOR: 'A folder name cannot contain path separators.',
      SETTINGS_FORBIDDEN: 'These settings cannot be changed here.',
      SETTINGS_UNKNOWN: 'Unknown settings.',
      NOT_FOUND: 'Not found.',
    },

    backendUnreachable: 'Cannot reach the backend. Start it with: python src/main.py --web-ui',
    requestFailed: 'Request failed (HTTP {status})',
  },
}
