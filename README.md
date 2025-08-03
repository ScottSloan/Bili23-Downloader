# Bili23-Downloader
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Platform](https://img.shields.io/badge/Platform-Windows_|_Linux_|_macOS-blue?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat) ![Build](https://img.shields.io/github/actions/workflow/status/ScottSloan/Bili23-Downloader/publish_release.yml)

![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.12.10-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.3-green?style=flat) 

[项目官网](https://bili23.scott-sloan.cn/)

Bili23 Downloader 是一款跨平台（Windows/Linux/macOS）的 B 站视频下载工具，支持下载 B 站投稿视频、番剧、电影等类型视频。支持多线程加速、断点续传等特性，搭配图形化界面与零配置操作，提供高效便捷的下载体验。

## 程序特性
* 跨平台（兼容 Windows、Linux、macOS 三大平台）
* GUI 图形化界面，零配置开箱即用，适配高分屏显示
* 支持解析UP主投稿视频、番剧、电影、课程等类型链接
* 支持自动识别短链接（b23.tv）、活动专题页（如拜年祭、二游新春会）链接
* 支持自定义下载视频分辨率、音质以及编码格式
* 支持 ASS 弹幕、字幕、封面下载
* 支持下载 Hi-Res 无损、杜比全景声音质
* 支持完整下载互动视频所有分支，自动生成可视化剧情树
* 支持断点续传、下载限速、多线程下载、并行下载、自动重试等功能
* 支持视频格式转换、片段截取、音频提取等功能

## 使用说明
有关本程序的使用说明，请参考[项目文档](https://bili23.scott-sloan.cn/doc/what-is-bili23-downloader.html)。

## 更新日志
## 1.65.0 (2025-08-03)
### 新增
* 支持调用系统默认浏览器实现 Web 页面显示
* 支持解析每周必看、排行榜链接
* 支持批量进行直播录制
* 支持自定义录制编码格式

### 优化
* 优化视频工具箱部分操作逻辑
* 优化二维码登录\短信登录相关逻辑
* 优化下载列表相关行为逻辑
* 优化下载异常处理机制

### 修复
* 修复单独下载 ass 文件时判定逻辑异常的问题
* 修复无法查看更新日志的问题
* 修复部分情况下 b23.tv 短链接无法识别的问题

## 免责声明
本项目仅供个人学习与研究用途，任何通过本项目下载的内容仅限于个人使用，用户自行承担使用本项目可能带来的所有风险。

本项目开发者不对因使用本项目所引发的任何法律纠纷、版权问题或其他损害承担责任。

本项目不拥有任何下载内容的版权，B站上的所有视频均为其原始版权方的财产。用户需遵守相关法律法规，且仅限于合理使用，不得进行任何形式的商业化传播或使用。

## 关于反病毒软件误报的说明
本程序使用了 Nuitka 工具进行封装。由于 Nuitka 的压缩和封装方式与一些木马较为相似，部分反病毒软件在扫描时可能会将其误判为威胁。这种误报并非表示程序本身有问题，而是因为反病毒软件通过特征匹配判断出风险。实际上，这种情况在使用 Nuitka 打包的 Python 程序中并不少见，很多恶意程序也使用了同样的工具进行分发，导致反病毒软件难以区分。

解决方案：

* 如果您希望避免误报，最稳妥的方式是：自行安装 Python 环境，从官方仓库克隆源代码后直接运行。

* 如果确实需要使用预编译版本，并且您信任本程序及开发者，也可以将程序添加到反病毒软件的白名单中。

* 本着安全第一的原则，如果确实对本程序及开发者不信任，请使用其他同类工具替代。

## 开源许可
本项目在 **MIT License** 许可协议下进行发布。

wbi 签名、部分接口以及 buvid3 等参数生成参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)  
编译版提供的 FFmpeg 来源于 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)  

## 联系方式
若遇到问题，请在 GitHub 中提出 issue。
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
