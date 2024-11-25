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
[![pAlhXgU.png](https://s21.ax1x.com/2024/09/27/pAlhXgU.png)](https://imgse.com/i/pAlhXgU)

#### **支持输入的 URL 链接**
| 类型 | 支持的功能 | 示例  |
| ---- | ---- | ---- |
| 用户投稿视频 （含分P，合集视频） | 解析下载 | https://www.bilibili.com/video/BV1t94y1C7fp |
| 剧集（含番剧、电影、纪录片、国创、电视剧、综艺） | 解析下载 | https://www.bilibili.com/bangumi/play/ss45574 |
| 直播 | m3u8直链解析、录制 | https://live.bilibili.com/1 |
| b23.tv 短链接 | 解析下载 | https://b23.tv/BV1UG411f7K1 |
| 活动页链接 | 解析下载 | https://www.bilibili.com/blackboard/topic/activity-jjR1nNRUF.html 

**注意：本程序不提供付费视频解析服务，请自行登录大会员账号后再进行使用。**

#### **部分类型可直接输入编号**
- 视频 av、BV 号
- 剧集 ep、md、ss 号

### **下载**
[![pAl4IxO.png](https://s21.ax1x.com/2024/09/27/pAl4IxO.png)](https://imgse.com/i/pAl4IxO)

# 更新日志
### **Version 1.53.0 (2024/11/25)**
Version 1.53.0 Beta5 发布

本次更新内容：
* 重构下载功能，解决历史遗留问题
* 支持动态调整并行下载数
* 支持将下载的 m4a 音频转换为 mp3 格式
* 支持视频封面提取功能和视频弹幕下载功能
* 支持调用系统默认播放器播放直播视频流
* 新增下载选项对话框，可修改清晰度和音频等设置
* 适配 Linux 平台深色模式
* 并行下载数最大可设置 8 个
* 下载失败的任务支持继续下载，保留下载进度
* 优化部分界面显示效果
* 修复名称以"-"开头的视频无法合成的问题
* 修复 Linux/macOS 平台无法选择播放器路径的问题

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
