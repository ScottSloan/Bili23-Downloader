# Bili23-Downloader
<p align="center">
    <a href="https://bili23.scott-sloan.cn" target="_blank">
        <img src="https://bili23.scott-sloan.cn/logo.png" alt="Bili23 Downloader" style="width: 500px;"/>
    </a>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/GitHub-black?logo=github&style=flat-square" alt="GitHub"/>
    <img src="https://img.shields.io/badge/Platform-Windows-blue?style=flat-square" alt="Platform"/>
    <img src="https://img.shields.io/badge/license-GPLv3-orange?style=flat-square" alt="License"/>
    <img src="https://img.shields.io/github/actions/workflow/status/ScottSloan/Bili23-Downloader/publish.yml?style=flat-square" alt="Build"/>
</p>

<p align="center">
    <img src="https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat-square" alt="Version"/>
    <img src="https://img.shields.io/badge/Python-3.12.10-green?style=flat-square" alt="Python"/>
    <img src="https://img.shields.io/badge/PySide6-6.10.2-green?style=flat-square" alt="PySide6"/>
</p>

<p align="center">
    <a href="https://bili23.scott-sloan.cn/doc/intro.html"><b>说明文档</b></a> •
    <a href="README.md"><b>中文</b></a> •
    <a href="README_en.md"><b>English</b></a>
</p>

<p align="center">
    <strong>Bili23 Downloader</strong> 是一款拥有现代 UI 的高质量跨平台 B 站视频下载工具。<br />
    不仅支持多线程加速、音视频流分离、弹幕与字幕下载以及 NFO 元数据刮削，<br />
    还具备高度自定义的文件分类与命名能力，完美兼容 Windows（含 Win7）、Linux 和 macOS 系统。
</p>

## 🌟 社区交流

## ⚡ 程序特性

| 特性 | 详细说明 |
| :--- | :--- |
| 🖥️ **Windows 支持** | 完美兼容 **Windows** 桌面操作系统（含 Win 7）。 |
| 🎨 **现代 UI 设计** | 基于 Fluent Design 设计语言，支持浅色 / 深色主题无缝切换，原生适配高分屏。 |
| 🚀 **多线程与加速** | 原生集成多线程并行下载、断点续传及网络异常自动重试机制，提供极致的下载速率。 |
| 🔗 **多网站解析** | 支持 **Bilibili**、**YouTube** 等主流视频平台，基于 yt-dlp 引擎实现全网站视频下载。 |
| ⚙️ **音视频自定义** | **画质**：`8K`、`4K`、`HDR`、`杜比视界`等<br>**音质**：`Hi-Res 无损`、`杜比全景声`等<br>**编码**：`AVC`、`HEVC`、`AV1` |
| 💬 **弹幕与字幕** | **弹幕**：`xml`、`ass`、`json`<br>**字幕**：`srt`、`lrc`、`txt`、`ass`、`json` |
| 🖼️ **封面解析嵌入** | 无损保存原图质量（`jpg`、`png`、`avif`、`webp`），并原生支持将图片自动嵌入最终的视频文件中。 |
| 🧩 **NFO 元数据** | 自动刮削并生成符合 **Kodi**、**Jellyfin**、**Emby** 等媒体中心标准格式的本地媒体元数据。 |
| 📁 **分类与命名** | 内置强大规则引擎，支持高度自定义的本地文件命名模板与多级目录分类存储模式。 |
| 📦 **封装格式转化** | 智能音视频流混合提取，支持封装输出为 `mp4` 或 `mkv`，充分满足不同播放设备的兼容需求。 |
| 🌐 **国际化支持** | 内置多语言界面，开箱可用：简体中文、繁体中文、English。 |
| 📖 **完全开源免费** | 基于 **GPL-3.0** 协议发布，代码完全开源、无内购、无广告，拥抱社区共建。 |

## 📦 环境依赖

本项目需要以下外部依赖，请在运行前确保已安装：

### FFmpeg
用于音视频流处理和合并，[下载 FFmpeg](https://ffmpeg.org/download.html)

### Node.js
用于 yt-dlp 部分功能支持，[下载 Node.js](https://nodejs.org/)
