# Bili23-Downloader-GUI
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.11.9-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.2-green?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat)

Bili23 Downloader GUI

下载 Bilibili 视频/番剧/电影/纪录片 等资源  

跨平台的 Bilibili 视频下载工具，支持 Windows、Linux*、macOS* 三平台。

* Linux、MacOS 适配工作正在全力推进中，目前基本功能可正常使用，如需尝鲜，请切换至 dev 分支，自行下载源码运行

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
### **Version 1.45 (2024/09/05)**
Version 1.45 正式版发布

本次更新内容：
* 支持对单个下载任务进行限速
* 支持对视频合成失败的任务进行重新合成
* 优化编译参数，大幅缩减程序体积，同时提升兼容性
* 修复下载大文件缓慢的问题
* 修复偶然情况下导致的下载失败的问题
* 修复由于编译器原因而导致无法合成视频的问题
* 修复视频合成完毕后仍有文件残留的问题

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
