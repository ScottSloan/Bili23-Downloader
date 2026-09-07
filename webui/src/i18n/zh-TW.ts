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

  auth: {
    title: '登入',
    hint: '口令在首次啟動時印到主控台，只顯示一次，且不會寫入日誌檔案。',
    username: '使用者名稱',
    password: '口令',
    submit: '登入',
    submitting: '登入中',
    failed: '使用者名稱或口令不正確。',
    expired: '登入已過期，請重新登入。',
    signOut: '登出 WebUI',
  },

  error: {
    backendUnreachable: '無法連線到後端，請先執行：python src/main.py --web-ui',
    requestFailed: '請求失敗（HTTP {status}）',
  },
}
