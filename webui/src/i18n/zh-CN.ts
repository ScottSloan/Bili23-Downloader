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

  error: {
    backendUnreachable: '无法连接到后端，请确认桌面版正在运行且已启用 MCP 服务',
    requestFailed: '请求失败（HTTP {status}）',
  },
}
