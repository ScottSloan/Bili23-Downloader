# Bili23-Downloader-GUI
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.11.9-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.1-green?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat)

Bili23 Downloader GUI

下载 Bilibili 视频/番剧/电影/纪录片 等资源  

### **导航**
+ [下载地址](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [更新日志](#更新日志) 
+ [联系方式](#联系方式)

### **Bili23 Downloader 系列**
* GUI 桌面端版本 (本项目)
* [CLI 命令行版本](https://github.com/ScottSloan/Bili23-Downloader-CLI) 

# 使用说明
本页仅简要展示，完整的使用说明请移步至 [Bili23 Downloader 使用说明](https://scott-sloan.cn/archives/12/)。

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
### **Version 1.44 (2024/08/07)**
Version 1.44 正式版发布

本次更新内容：
* 新增“格式转换”工具，可调整视频格式、编码和比特率，支持调用 GPU 加速
* 新增视频封面查看功能，可在下载窗口中点击视频封面，支持保存视频封面
* 视频合成失败时，可查看错误详情
* 调整部分界面的图标大小和组件边距
* 优化视频封面显示效果，不再以第一帧作为封面
* 修复部分视频清晰度识别不全的问题
* 修复特定情况下恢复视频下载导致卡死的问题
* 修复 FFmpeg 可用性判定异常的问题

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
