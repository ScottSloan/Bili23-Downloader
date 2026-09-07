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

    group: {
      interface: 'Interface',
      download: 'Download',
      behavior: 'Behavior',
      additional: 'Danmaku, Subtitles, Cover, Chapters, and Metadata',
      advanced: 'Advanced',
      aria2: 'aria2',
      webui: 'WebUI',
    },

    label: {
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
    backendUnreachable: 'Cannot reach the backend. Start it with: python src/main.py --web-ui',
    requestFailed: 'Request failed (HTTP {status})',
  },
}
