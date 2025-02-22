import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Bili23 Downloader",
  description: "一个 B 站视频下载工具",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      {
        text: '首页',
        link: '/'
      },
      {
        text: '文档',
        link: '/doc/intro'
      },
      {
        text: '博客',
        link: 'https://www.scott-sloan.cn'
      }
    ],

    sidebar: [
      {
        text: '简介',
        items: [
          {
            text: 'Bili23 Downloader 简介',
            link: '/doc/intro'
          }
        ]
      },
      {
        text: '安装',
        collapsed: true,
        items: [
          {
            text: '安装主程序',
            link: '/doc/install/main'
          },
          {
            text: '安装 FFmpeg',
            link: '/doc/install/ffmpeg'
          }
        ]
      },
      {
        text: '使用',
        collapsed: true,
        items: [
          {
            text: '基础使用',
            link: '/doc/use/basic'
          },
          {
            text: '支持的链接',
            link: '/doc/use/url'
          }
        ]
      },
      {
        text: '更新记录',
        collapsed: true,
        items: [
          {
            text: '1.50',
            collapsed: true,
            items: [
              {
                text: '1.55.0',
                link: '/doc/history/log_1550'
              },
              {
                text: '1.54.0',
                link: '/doc/history/log_1540'
              },
              {
                text: '1.53.0',
                link: '/doc/history/log_1530'
              },
              {
                text: '1.52.0',
                link: '/doc/history/log_1520'
              },
              {
                text: '1.51.0',
                link: '/doc/history/log_1510'
              },
              {
                text: '1.50.0',
                link: '/doc/history/log_1500'
              }
            ]
          },
          {
            text: '1.40',
            collapsed: true,
            items: [
            ]
          }
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
