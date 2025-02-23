import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Bili23 Downloader",
  description: "一个 B 站视频下载工具",
  lastUpdated: true,
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      {
        text: '首页',
        link: '/'
      },
      {
        text: '文档',
        link: '/doc'
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
            link: '/doc'
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
                text: '1.51.1',
                link: '/doc/history/log_1511'
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
              {
                text: '1.45.0',
                link: '/doc/history/log_1450'
              },
              {
                text: '1.44.0',
                link: '/doc/history/log_1440'
              },
              {
                text: '1.43.0',
                link: '/doc/history/log_1430'
              },
              {
                text: '1.42.0',
                link: '/doc/history/log_1420'
              },
              {
                text: '1.41.0',
                link: '/doc/history/log_1410'
              },
              {
                text: '1.40.0',
                link: '/doc/history/log_1400'
              }
            ]
          },
          {
            text: '1.30',
            collapsed: true,
            items: [
              {
                text: '1.36.0',
                link: '/doc/history/log_1360'
              },
              {
                text: '1.35.0',
                link: '/doc/history/log_1350'
              },
              {
                text: '1.34.0',
                link: '/doc/history/log_1340'
              },
              {
                text: '1.33.0',
                link: '/doc/history/log_1330'
              },
              {
                text: '1.32.0',
                link: '/doc/history/log_1320'
              },
              {
                text: '1.31.0',
                link: '/doc/history/log_1310'
              },
              {
                text: '1.30.0',
                link: '/doc/history/log_1300'
              }
            ]
          },
          {
            text: '1.20',
            collapsed: true,
            items: [
              {
                text: '1.21.0',
                link: '/doc/history/log_1210'
              },
              {
                text: '1.20.0',
                link: '/doc/history/log_1200'
              }
            ]
          },
          {
            text: '1.10',
            collapsed: true,
            items: [
              {
                text: '1.14.0',
                link: '/doc/history/log_1140'
              },
              {
                text: '1.13.1',
                link: '/doc/history/log_1131'
              },
              {
                text: '1.13.0',
                link: '/doc/history/log_1130'
              },
              {
                text: '1.12.0',
                link: '/doc/history/log_1120'
              },
            ]
          }
        ]
      },
      {
        text: '常见问题',
        items: [

        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ScottSloan/Bili23-Downloader' }
    ],

    search: {
      provider: 'local'
    },

    docFooter: {
      prev: '上一页',
      next: '下一页'
    },
    
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '菜单',
    outlineTitle: '目录'
  }
})
