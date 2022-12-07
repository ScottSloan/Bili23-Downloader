# Bili23-Downloader-GUI
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.9.12-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.0-green?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat)


Bili23 Downloader GUI 桌面端版本

下载 Bilibili 视频/番剧/电影/纪录片 等资源  

### **导航**
+ [下载地址](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [TODO](#todo)
+ [更新日志](#更新日志) 
+ [联系方式](#联系方式)

### **Bili23 Downloader 系列**
* GUI 桌面端版本 (本项目)
* [CLI 命令行版本](https://github.com/ScottSloan/Bili23-Downloader-CLI) (现已上线，欢迎体验)

# 使用说明
### **安装主程序**

请前往 [Release](https://github.com/ScottSloan/Bili23-Downloader/releases) 页面，下载最新版本。

### **主界面**
[![zUM8v6.png](https://s1.ax1x.com/2022/11/27/zUM8v6.png)](https://imgse.com/i/zUM8v6)

### **支持输入的 URL 链接**
* 用户投稿类型视频链接
* 剧集（番剧，电影，纪录片等）链接
* 活动页链接
* 直播链接
* 课程链接
* 音乐、歌单链接
* b23.tv 短链接

### **部分类型可直接输入编号**
- 视频 av、BV 号
- 剧集 epid、md、ss 号
- 音乐 au 号、歌单 am 号

### **下载**
[![zUMYDO.png](https://s1.ax1x.com/2022/11/27/zUMYDO.png)](https://imgse.com/i/zUMYDO)

下载模块使用流式下载实现，默认开启 4 个线程以提升下载速度，理论上可以跑满带宽，实际速度取决于B站服务器状况。

程序默认下载 `HEVC/H.265` 编码的 `1080P` 视频，您可在设置中更改。若视频不含所选的清晰度或编码，程序将自动下载可用的最高清晰度或编码。

> 请注意，关闭程序后未完成的任务需重新下载。

### **登录**
#### **支持的登录方式**
* 扫码登录
* Cookie 登录 (SESSDATA 字段)

未登录状态下您只能下载到 `480P` 视频，若您想下载更高清晰度的视频，请登录使用。

> 登录有效期为半年，过期后需重新登录。

### **其他功能**
- 支持显示非正片剧集，如花絮、PV、OP、ED等  
- 下载弹幕 (保存为 `xml` 格式)  
- 下载字幕 (保存为 `srt` 格式，如有多个字幕将全部下载)  
- 下载歌词 (保存为 `lrc` 格式)
- 支持网络代理和代理身份验证
- 支持下载 `AVC/H.264`，`HEVC/H.265` 和 `AV1` 编码格式视频 (取决于视频支持)

# **TODO**
- [X] **视频**
  - [X] 用户投稿视频
  - [ ] 互动视频
- [X] **剧集**
  - [X] 番剧
  - [X] 电影
  - [X] 纪录片
  - [X] 国创
  - [X] 综艺
  - [X] 电视剧
- [X] **音频**
  - [X] 音乐
  - [X] 歌单
- [X] **直播**
- [X] **课程**
- [ ] **漫画**
- [ ] **专栏**
- [X] **其他**
  - [ ] 登录
    - [ ] 账号密码登录
    - [ ] 短信登录
    - [X] 扫码登录
    - [X] Cookie 登录
  - [X] 下载弹幕
  - [X] 下载字幕
  - [X] 下载歌词

# 更新日志
### **Version 1.35 (2022-12-7)**
本次更新内容如下：
* 优化调试功能
* 优化代码结构
* 再次修复视频无法下载的问题
* 修复无法检查更新的问题

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: https://scott.o5g.top
