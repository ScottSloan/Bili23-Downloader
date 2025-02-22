import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Bili23 Downloader",
  description: "一个B 站视频下载工具",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: '首页', link: '/' },
      { text: '文档', link: '/doc' },
      { text: '博客', link: 'https://www.scott-sloan.cn'}
    ],

    sidebar: [
      {
        text: '简介',
        items: [
          { text: 'Bili23 Downloader 简介', link: '/doc/intro-bili23'}
        ]
      },
      {
        text: '安装',
        items: [
          { text: '安装主程序', link: '/doc/install-main' },
          { text: '安装 FFmpeg', link: '/doc/install-ffmpeg' }
        ]
      },
      {
        text: '使用',
        items: [
          { text: '解析流程', link: '/doc/use-process'},
          { text: '支持链接', link: '/doc/use-url'}
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ScottSloan/Bili23-Downloader' }
    ],

    search: {
      provider: 'local'
    }
  }
})
