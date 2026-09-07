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
    tagDownloaded: '已下载',
    tagNeedsReparse: '需二次解析',
  },

  user: {
    signedOut: '未登录',
    avatarAlt: '用户头像',
  },

  settings: {
    title: '设置',
    theme: {
      label: '主题',
      light: '浅色',
      dark: '深色',
      system: '系统默认',
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
