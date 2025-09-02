import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  lang: 'zh-CN',
  title: "Bili23 Downloader",
  description: "跨平台的 B 站视频下载工具，支持 Windows、Linux、macOS 三平台，下载 B 站视频/番剧/电影/纪录片 等资源",
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
        link: '/doc/what-is-bili23-downloader'
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
            text: 'Bili23 Downloader 是什么？',
            link: '/doc/what-is-bili23-downloader'
          }
        ]
      },
      {
        text: '安装',
        collapsed: true,
        items: [
          {
            text: '安装程序',
            link: '/doc/install/main'
          },
          {
            text: '安装 FFmpeg',
            link: '/doc/install/ffmpeg'
          },
          {
            text: '安装 VLC Media Player',
            link: '/doc/install/vlc'
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
          },
          {
            text: '进阶使用',
            collapsed: true,
            items: [
              {
                text: '使用代理',
                link: '/doc/use/advanced/proxy'
              },
              {
                text: '并行下载',
                link: '/doc/use/advanced/parallel_downloading'
              },
              {
                text: '替换音视频流 CDN 节点',
                link: '/doc/use/advanced/cdn_host'
              },
              {
                text: '自定义下载文件名&自动分类',
                link: '/doc/use/advanced/custom_file_name'
              },
              {
                text: '互动视频剧情树',
                link: '/doc/use/advanced/interact_video_graph'
              },
              {
                text: '下载 ASS 格式的弹幕和字幕',
                link: '/doc/use/advanced/ass'
              }
            ],
          },
          {
            text: '更新程序',
            link: '/doc/use/update'
          }
        ]
      },
      {
        text: '常见问题',
        collapsed: true,
        items: [
          {
            text: '运行相关',
            link: '/doc/faq/run'
          },
          {
            text: '下载相关',
            link: '/doc/faq/download'
          },
          {
            text: '其他问题',
            link: '/doc/faq/other'
          }
        ]
      },
      {
        text: '社区交流',
        link: '/doc/community'
      },
      {
        text: '免责声明',
        link: '/doc/announcement'
      },
      {
        text: '开源许可',
        link: '/doc/license'
      },
      {
        text: '支持我们',
        link: '/doc/sponsor'
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ScottSloan/Bili23-Downloader' },
      { icon: 'qq', link: 'https://qm.qq.com/q/KX3uJIFIYK' }
    ],

    search: {
      provider: 'local',
      options: {
        translations: {
          button: {
            buttonText: '搜索文档',
            buttonAriaLabel: '搜索文档'
          },
          modal: {
            searchBoxPlaceholder: '搜索文档',
            displayDetails: '显示详情',
            backButtonTitle: '后退',
            resetButtonTitle: '清除查询条件',
            footer: {
              selectText: '选择',
              closeText: '关闭',
              navigateText: '导航'
            }
          }
        }
      }
    },

    docFooter: {
      prev: '上一页',
      next: '下一页'
    },

    lastUpdated: {
      text: '最后更新于',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'medium'
      }
    },

    footer: {
      copyright: 'Copyright © 2025 Scott Sloan. All Rights Reserved.',
      message: '<a href="https://beian.miit.gov.cn/" target="_blank">滇ICP备2023007640号-1</a>'
    },
    
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '菜单',
    outlineTitle: '页面导航'
  }
})
