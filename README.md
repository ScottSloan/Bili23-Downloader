# Bili23-Downloader
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Platform](https://img.shields.io/badge/Platform-Windows_|_Linux_|_macOS-blue?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat) ![Build](https://img.shields.io/github/actions/workflow/status/ScottSloan/Bili23-Downloader/release_build.yml)

![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.11.9-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.2-green?style=flat) 

[项目官网](https://bili23.scott-sloan.cn/)

Bili23 Downloader 是一款跨平台的 B 站视频下载工具，支持 Windows、Linux、macOS 三平台，能够下载 B 站视频/番剧/电影/纪录片等资源。

## 程序特性
* 跨平台(Windows/Linux/macOS)
* 提供 GUI 图形界面
* 简洁易用，适配高分屏缩放
* 支持投稿视频\剧集\课程\直播链接解析
* 支持短链接\活动页（如拜年祭、二游新春会）链接解析
* 支持弹幕\字幕\封面下载
* 支持修改剧集列表显示方式，一键显示全部视频
* 支持自定义清晰度\音质\视频编码
* 支持仅下载音频，最高可下载 Hi-Res 无损音质
* 简洁美观且强大的下载管理界面，批量管理下载任务
* 支持断点续传\下载限速\多线程下载\并行下载\自动重试等功能
* 简洁易用的设置界面，无需参照文档手动修改配置文件

## 使用说明
有关本程序的使用说明，请参考[项目文档](https://bili23.scott-sloan.cn/doc/waht-is-bili23-downloader.html)。

## 更新日志
### 1.61.0 (2025-03-23)
#### 新增

#### 优化
* 优化对话框创建逻辑，避免重复创建消耗额外内存

#### 修复
* 修复只能视频下载 H.264 编码的问题
* 修复合集中的分 P 视频无法下载的问题
* 修复高缩放倍数下二维码显示不完整的问题

## 免责声明
本项目仅供个人学习与研究用途，任何通过本项目下载的内容仅限于个人使用，用户自行承担使用本项目可能带来的所有风险。

本项目开发者不对因使用本项目所引发的任何法律纠纷、版权问题或其他损害承担责任。

本项目不拥有任何下载内容的版权，B站上的所有视频均为其原始版权方的财产。用户需遵守相关法律法规，且仅限于合理使用，不得进行任何形式的商业化传播或使用。

## 开源许可
本项目在 **MIT License** 许可协议下进行发布。

wbi 签名、部分接口以及 buvid3 等参数生成参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)  
编译版提供的 FFmpeg 来源于 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)  

## 联系方式
若遇到问题，请在 GitHub 中提出 issue。
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
