# Bili23-Downloader-GUI
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.11.9-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.2-green?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat)

Bili23 Downloader GUI

跨平台的 B 站视频下载工具，支持 Windows、Linux、macOS 三平台，下载 B 站视频/番剧/电影/纪录片 等资源  

### **导航**
+ [下载地址](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [更新日志](#更新日志) 
+ [联系方式](#联系方式)

### **Bili23 Downloader 系列**
* GUI 桌面端版本 (本项目)
* [CLI 命令行版本](https://github.com/ScottSloan/Bili23-Downloader-CLI) 

# 使用说明
本页面仅简要展示，完整的使用说明请移步至 [Bili23 Downloader 使用说明](https://www.scott-sloan.cn/archives/12/)。

### **主界面**
[![pkAukBd.png](https://s21.ax1x.com/2024/05/04/pkAukBd.png)](https://imgse.com/i/pkAukBd)

#### **支持输入的 URL 链接**
| 类型 | 示例  |
| ---- | ---- |
| 用户投稿视频 | https://www.bilibili.com/video/BV1t94y1C7fp |
| 剧集（番剧、电影、纪录片等） | https://www.bilibili.com/bangumi/play/ss45574 |
| b23.tv 短链接 | https://b23.tv/BV1UG411f7K1 |
| 活动页链接 | https://www.bilibili.com/blackboard/topic/activity-jjR1nNRUF.html |

#### **部分类型可直接输入编号**
- 视频 av、BV 号
- 剧集 ep、md、ss 号

### **下载**
[![pkAuu38.png](https://s21.ax1x.com/2024/05/04/pkAuu38.png)](https://imgse.com/i/pkAuu38)

### **登录**
由于B站限制，未登录状态下只能获取到 `480P` 视频，因此建议您扫码登录后使用。

> 登录有效期为半年，过期后需重新登录。

# 更新日志
### **Version 1.50 (2024/09/27)**
Version 1.50 正式版发布

本次更新内容：
* 支持 Linux 与 macOS 平台
* 适配 macOS 深色模式
* 新增“自动”清晰度选项，程序将自动下载每个视频的最高可用清晰度
* 新增“仅下载音频”选项，支持单独下载视频的音轨
* 为部分设置选项添加了注释说明
* 优化视频封面显示效果，支持 16:9 和 16:10 两种封面显示
* 优化下载窗口调整大小时的显示效果
* 优化剧集列表解析方式，支持解析视频所在的合集
* 优化断点续传相关功能
* 调整默认下载多线程数为 2 个
* 修复设置中修改并行下载数时下载窗口不同步更新的问题
* 修复下载路径含空格或中文时而导致无法合成的问题
* 修复部分情况下下载停止无法继续的问题
* 修复部分情况下无法停止下载的问题
* 修复批量下载视频完成后无法打开文件所在位置的问题
* 修复部分情况下无法获取错误日志的问题

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
