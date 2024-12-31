# Bili23-Downloader-GUI
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.11.9-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.2-green?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat) 

![Windows](https://img.shields.io/badge/-Windows-blue?logo=windows) ![Linux](https://img.shields.io/badge/-Linux-333?logo=ubuntu) ![macOS](https://img.shields.io/badge/-MacOS-black?logo=apple)

Bili23 Downloader GUI

跨平台的 B 站视频下载工具，支持 Windows、Linux、macOS 三平台，下载 B 站视频/番剧/电影/纪录片 等资源  

### **导航**
+ [下载地址](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [更新日志](#更新日志) 
+ [免责声明](#免责声明) 
+ [开源许可](#开源许可) 
+ [联系方式](#联系方式)

### **Bili23 Downloader 系列**
* GUI 桌面端版本 (本项目)
* [CLI 命令行版本](https://github.com/ScottSloan/Bili23-Downloader-CLI) 

# 使用说明
本页面仅简要展示，完整的使用说明请移步至 [Bili23 Downloader 使用说明](https://www.scott-sloan.cn/archives/12/)。

### **主界面**
[![pAxOkb6.png](https://s21.ax1x.com/2024/12/30/pAxOkb6.png)](https://imgse.com/i/pAxOkb6)

#### **支持输入的 URL 链接**
| 类型 | 支持的功能 | 示例 |
| ---- | ---- | ---- |
| 用户投稿视频（含分P，合集视频） | 解析下载 | https://www.bilibili.com/video/BV1t94y1C7fp |
| 剧集（含番剧、电影、纪录片、国创、电视剧、综艺） | 解析下载 | https://www.bilibili.com/bangumi/play/ss45574 |
| 课程 | 解析下载 | https://www.bilibili.com/cheese/play/ep69165 |
| 直播 | m3u8直链解析、录制 | https://live.bilibili.com/1 |
| b23.tv 短链接 | 解析下载 | https://b23.tv/BV1UG411f7K1 |
| 活动页链接 | 解析下载 | https://www.bilibili.com/blackboard/topic/activity-jjR1nNRUF.html 

**注意：本程序不提供付费视频解析服务，请自行登录大会员账号后再进行使用。**

#### **部分类型可直接输入编号**
- 视频 av、BV 号
- 剧集 ep、md、ss 号

#### **支持下载的弹幕&字幕&封面格式**
| 类型 | 支持下载的格式 | 备注 |
| ---- | ---- | ---- |
| 弹幕 | xml, protobuf | |
| 字幕 | srt, txt, json | 需要登录才可下载 |
| 封面 | jpg | |

解析完成后，点击右上角小齿轮图标可自定义清晰度和音质等设置。

[![pAxXee0.png](https://s21.ax1x.com/2024/12/30/pAxXee0.png)](https://imgse.com/i/pAxXee0)

点击列表图标可切换剧集列表显示方式。

[![pAxXRk8.png](https://s21.ax1x.com/2024/12/30/pAxXRk8.png)](https://imgse.com/i/pAxXRk8)

### **下载**
[![pAl4IxO.png](https://s21.ax1x.com/2024/09/27/pAl4IxO.png)](https://imgse.com/i/pAl4IxO)

程序支持多线程下载（最多 8 线程）、并行下载（上限为 8 个，支持动态调整）、断点续传、下载限速、出错重试等功能。

# 更新日志
### **Version 1.54 (2025/01/01)**
Version 1.54.0 正式版 发布

本次更新内容：
* 新增剧集列表显示菜单，可快速修改剧集列表显示方式
* 支持解析下载课程类链接
* 支持替换音视频流 CDN，可自动切换或手动指定
* 支持下载视频字幕，可保存为 srt, txt, json 三种格式
* 支持解析合集中的分 P 视频
* 部分接口添加 wbi 签名，避免账号被风控
* 优化部分界面显示效果
* 优化异常处理机制
* 程序配置文件采用 json 格式存储
* 修复设置合成页面的修改无法保存的问题
* 修复手动指定播放器无效的问题
* 修复部分情况下视频下载失败的问题

# 免责声明
本项目仅供个人学习与研究用途，任何通过本项目下载的内容仅限于个人使用，用户自行承担使用本项目可能带来的所有风险。

本项目开发者不对因使用本项目所引发的任何法律纠纷、版权问题或其他损害承担责任。

本项目不拥有任何下载内容的版权，B站上的所有视频均为其原始版权方的财产。用户需遵守相关法律法规，且仅限于合理使用，不得进行任何形式的商业化传播或使用。

# 开源许可
本项目在 **MIT License** 许可协议下进行发布

wbi 签名以及部分接口参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)  
编译版提供的 FFmpeg 来源于 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)  

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
