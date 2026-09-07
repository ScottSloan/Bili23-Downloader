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
    loading: '正在讀取設定…',
    saving: '正在儲存…',
    saveFailed: '儲存失敗：{message}',
    restartBadge: '需重新啟動',
    restartNotice: '以下設定需要重新啟動後端後生效：{items}',
    localOnly: '僅儲存於目前瀏覽器',

    theme: {
      label: '主題',
      description: '選擇應用程式主題',
      light: '淺色',
      dark: '深色',
      system: '系統預設',
    },

    accent: {
      label: '強調色',
      description: '自訂應用程式中使用的強調色',
      reset: '恢復預設',
    },

    group: {
      interface: '介面',
      download: '下載',
      behavior: '行為',
      additional: '彈幕、字幕、封面、章節與元數據',
      advanced: '進階',
      aria2: 'aria2',
      webui: 'WebUI',
    },

    label: {
      language: '語言',

      download_path: '下載路徑',
      download_thread: '多執行緒數',
      download_parallel: '平行下載數',
      speed_limit_enabled: '下載速度限制',
      speed_limit_rate: '限速值',
      video_container: '輸出容器格式',
      m4a_to_mp3: '將 M4A 轉換為 MP3',

      show_download_options_dialog: '下載時顯示選項對話方塊',
      duplicate_download_resolution: '重複下載處理',
      file_conflict_resolution: '同名檔案處理',

      download_danmaku: '下載彈幕',
      danmaku_type: '彈幕格式',
      embed_danmaku: '嵌入彈幕',
      delete_danmaku_after_embed: '嵌入後刪除彈幕檔案',
      download_subtitle: '下載字幕',
      subtitle_type: '字幕格式',
      embed_subtitle: '嵌入字幕',
      delete_subtitle_after_embed: '嵌入後刪除字幕檔案',
      download_cover: '下載封面',
      cover_type: '封面格式',
      attach_cover: '嵌入封面',
      delete_cover_after_attach: '嵌入後刪除封面',
      embed_chapter: '嵌入章節資訊',
      download_metadata: '下載元數據',
      metadata_type: '元數據格式',

      prefer_cdn_server_provider: '優先使用服務商 CDN',
      area: '所在地區',
      ffmpeg_source: 'FFmpeg 來源',
      custom_ffmpeg_path: '自訂 FFmpeg 路徑',
      proxy_mode: '代理模式',
      proxy_server: '代理伺服器',
      proxy_port: '代理連接埠',
      proxy_uname: '代理使用者名稱',
      proxy_password: '代理密碼',
      user_agent: '自訂 User-Agent',

      aria2_managed: '由 Bili23 託管',
      aria2_path: 'aria2c 路徑',
      aria2_rpc_host: 'RPC 位址',
      aria2_rpc_port: 'RPC 連接埠',

      webui_host: '監聽位址',
      webui_port: '連接埠',
      webui_username: '使用者名稱',
      webui_session_hours: '登入有效期',
    },

    desc: {
      language: '選擇應用程式的顯示語言',

      download_path: '下載檔案的儲存位置。已在佇列中的任務仍使用建立時的目錄。',
      download_thread: '調整單一任務使用的執行緒數，預設為 4',
      download_parallel: '調整同時下載的任務數，預設為 1',
      speed_limit_enabled: '限制所有任務的總下載速度',
      video_container: '選擇最終輸出影片檔案的容器格式',
      m4a_to_mp3: '僅於下載純音訊串流時有效',

      show_download_options_dialog: '開始下載前跳出對話方塊以自訂本次下載設定',
      duplicate_download_resolution:
        '選擇偵測到重複下載時的操作。WebUI 沒有可詢問的對象，因此設為「總是詢問」時會直接跳過。',
      file_conflict_resolution: '選擇當目標位置已存在同名檔案時的操作',

      embed_danmaku: '將彈幕作為字幕軌嵌入至影片檔案中，僅在彈幕格式為 ASS 且輸出容器為 MKV 時可用',
      delete_danmaku_after_embed: '將彈幕嵌入影片檔案後刪除原彈幕檔案',
      embed_subtitle:
        '將字幕作為字幕軌嵌入至影片檔案中，僅在字幕格式為 ASS 且輸出容器為 MKV 時可用',
      delete_subtitle_after_embed: '將字幕嵌入影片檔案後刪除原字幕檔案',
      attach_cover: '將下載的封面嵌入至影片檔案中',
      delete_cover_after_attach: '將封面嵌入影片檔案後刪除原封面檔案',
      embed_chapter: '將影片的分段章節寫入影片檔案，僅在合併影片與音訊時生效',

      prefer_cdn_server_provider: '優先使用伺服器供應商提供的 CDN，提升下載穩定性',
      area: '選擇實際位置，以自動匹配更合適的 CDN 伺服器並提升下載速度',
      ffmpeg_source: '選擇要使用的 FFmpeg 可執行檔',
      proxy_mode: '選擇用於解析與下載的代理',
      user_agent: '為網路請求設定自訂 User-Agent 字串',

      aria2_managed: '隨 WebUI 一起啟動與停止 aria2。關閉後將連線至你自行執行的 aria2。',
      aria2_path: '留空則於系統環境變數中尋找 aria2c',
      aria2_rpc_host: 'aria2 監聽 RPC 的位址',

      webui_host: '填 127.0.0.1 只接受本機連線，填 0.0.0.0 則接受來自網路的連線',
      webui_username: '登入本頁面所用的帳號',
      webui_session_hours: '一次登入的有效時長',
    },

    option: {
      language: {
        zh_CN: '简体中文',
        zh_TW: '繁體中文',
        en_US: 'English',
        Auto: '系統預設',
      },
      area: {
        cn: '中國大陸',
        ov: '中國大陸以外地區（包括香港、澳門及台灣）',
      },
      ffmpeg_source: {
        bundled: '程式內建',
        system: '系統環境變數',
        custom: '自訂路徑',
      },
      proxy_mode: {
        disabled: '不使用代理',
        system: '使用系統代理',
        manual: '手動設定',
      },
      duplicate_download_resolution: {
        0: '繼續下載',
        1: '跳過',
        2: '總是詢問',
      },
      file_conflict_resolution: {
        1: '自動重新命名',
        2: '覆蓋檔案',
      },
    },

    picker: {
      title: '選取資料夾',
      locations: '位置',
      parent: '上一層',
      newFolder: '新增資料夾',
      newFolderPlaceholder: '資料夾名稱',
      create: '建立',
      empty: '此資料夾下沒有子資料夾。',
      truncated: '項目過多，僅顯示前 {count} 項。',
      choose: '使用此資料夾',
      cancel: '取消',
      failed: '無法開啟此資料夾：{message}',
      noRoots: '沒有設定可瀏覽的目錄。請在 config.json 中設定 webui_browse_roots。',
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
