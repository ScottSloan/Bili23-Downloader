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
    download: '下載選取項',
    nothingChecked: '沒有勾選任何內容。',
    created: '已建立 {count} 個任務（共勾選 {requested} 項）。',
    createdNone: '沒有建立任務，可能都已經在佇列中了。',
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

  download: {
    title: '下載 {count} 項',
    loading: '正在取得媒體資訊…',
    fallback: '首選的影片無法取得媒體資訊，以下畫質來自「{title}」。',
    videoQuality: '影片畫質',
    videoCodec: '影片編碼',
    audioQuality: '音質',
    extras: '同時下載',
    danmaku: '彈幕',
    subtitle: '字幕',
    cover: '封面',
    metadata: '中繼資料',
    cancel: '取消',
    confirm: '開始下載',
    submitting: '建立中',
  },

  task: {
    summary: '{total} 個任務，{active} 個進行中',
    offline: '即時更新已中斷',
    empty: '暫無下載任務。',
    completedSection: '已完成（{count}）',
    pause: '暫停',
    resume: '繼續',
    retry: '重新下載',
    remove: '刪除',
    status: {
      queued: '等待下載',
      parsing: '解析中',
      downloading: '下載中',
      paused: '已暫停',
      completed: '已完成',
      ffmpeg_queued: '等待處理',
      merging: '合併中',
      converting: '轉換中',
      additional_processing: '取得附加內容',
      failed: '下載失敗',
      ffmpeg_failed: '處理失敗',
      unknown: '未知',
    },
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
