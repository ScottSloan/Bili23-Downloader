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
    tagDownloaded: 'Downloaded',
    tagNeedsReparse: 'Needs re-parsing',
  },

  user: {
    signedOut: 'Not signed in',
    avatarAlt: 'User avatar',
  },

  settings: {
    title: 'Settings',
    theme: {
      label: 'Theme',
      light: 'Light',
      dark: 'Dark',
      system: 'System default',
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
    backendUnreachable:
      'Cannot reach the backend. Start it with: python src/main.py --web-ui',
    requestFailed: 'Request failed (HTTP {status})',
  },
}
