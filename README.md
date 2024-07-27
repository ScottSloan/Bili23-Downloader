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
### **Version 1.43 (2024/7/27)**
Version 1.43 正式版发布

本次更新内容：
* 支持“智能修复”清晰度视频的解析与下载（需要大会员）
* 视频合成失败时，将生成错误信息日志文件
* 更新 FFmpeg 版本至 7.0.1
* 优化用户登录信息保存方式，更新程序后无需重新登录
* 优化 FFmpeg 检测方式，支持自动检测和手动选取两种方式
* 优化视频封面显示效果，现在图片的质量提升，且以 16:9 比例显示
* 优化默认下载音质选项，将 Hi-Res 无损和杜比全景声归为同一类，程序将视视频支持情况切换下载音质
* 优化用户头像显示效果，添加圆形遮罩层
* 优化部分界面显示效果
* 修复部分下载记录无法清除的问题
* 修复恢复下载时无法正常显示提示的问题
* 修复杜比全景声音质下载无效的问题
* 修复未登录状态下下载无损或杜比全景声时无法继续的问题

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://www.scott-sloan.cn)
