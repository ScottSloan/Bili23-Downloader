// 繁體中文
//
// 與 GUI 共有的字串直接取自 src/res/i18n/bili23.zh_TW.ts，措辭保持一致。
// 缺失的鍵會回落到 en.js 的英文原文。

export default {
  nav: {
    parse: '解析',
    download: '下載',
    settings: '設定',
  },

  parse: {
    placeholder: '連結 / av / BV / ep / ss / md / 收藏夾 / 個人空間',
    submit: '解析',
    submitting: '解析中',
    empty: '解析結果會顯示在這裡。',
    summary: '{category}（共 {total} 項，已選 {checked} 項）',
    mediaUnavailable: '媒體資訊無法取得（{reason}），暫時無法下載',
    tagDownloaded: '已下載',
    tagNeedsReparse: '需二次解析',
  },

  user: {
    signedOut: '未登入',
    avatarAlt: '使用者頭像',
  },

  settings: {
    title: '設定',
    theme: {
      label: '主題',
      light: '淺色',
      dark: '深色',
      system: '系統預設',
    },
  },

  column: {
    number: '序號',
    title: '標題名稱',
    badge: '備註',
    duration: '時長',
    dyn_time: '發佈時間 / 收藏時間 / 上次觀看時間',
    pubtime: '發佈時間',
    favtime: '收藏時間',
    viewtime: '上次觀看時間',
  },

  error: {
    backendUnreachable: '無法連線到後端，請確認桌面版正在執行且已啟用 MCP 服務',
    requestFailed: '請求失敗（HTTP {status}）',
  },
}
