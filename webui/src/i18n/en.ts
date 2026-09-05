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

  error: {
    backendUnreachable:
      'Cannot reach the backend. Make sure the desktop app is running with the MCP service enabled.',
    requestFailed: 'Request failed (HTTP {status})',
  },
}
