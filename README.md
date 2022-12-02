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

### **安装 ffmpeg**
### **Windows 版本已经集成 ffmpeg，无需下载安装** 
ffmpeg 版本：5.1.2  
来源：[www.gyan.dev](https://www.gyan.dev)

### **Linux 用户请执行以下命令安装**

```
sudo apt install ffmpeg
```

### **主界面**
[![zUM8v6.png](https://s1.ax1x.com/2022/11/27/zUM8v6.png)](https://imgse.com/i/zUM8v6)

将 URL 链接粘贴到地址栏中，点击 `Get` 按钮解析 URL 链接。  
选择要下载的视频，点击 `下载视频` 按钮开始下载。

#### **支持输入的 URL 链接**
- 用户投稿类型视频链接
- 剧集（番剧，电影，纪录片等）链接
- 活动页链接
- 直播链接
- 音乐、歌单链接
- b23.tv 短链接

#### **部分类型可直接输入编号**
- 视频 av、BV 号
- 剧集 epid、md、ss 号
- 音乐 au 号、歌单 am 号

### **下载管理**
[![zUMYDO.png](https://s1.ax1x.com/2022/11/27/zUMYDO.png)](https://imgse.com/i/zUMYDO)

下载功能使用流式下载实现，大幅提升下载速度，经测试可跑满带宽。

> 关闭程序后未完成的任务需重新开始下载

### **用户中心**
目前可通过哔哩哔哩客户端扫描二维码登录，登录后可正常下载 1080P 及大会员视频。 

**此功能仅获取账号的 Cookie 中的 SESSDATA 字段，并保存在本地，不会泄露您的账号信息，您可以随时注销账户清除本地数据。**

> 每次登录有效期为一个月，过期后需重新登录

### **其他功能**
- 支持显示完整剧集列表，如 PV，OP，ED 等  
- 支持解析直播链接，并在播放器中播放
- 下载弹幕 (保存为 `xml` 格式)  
- 下载字幕 (保存为 `srt` 格式，如有多个字幕将全部下载)  
- 下载歌词 (保存为 `lrc` 格式)
- 支持网络代理  
- 支持下载 `AVC/H.264`，`HEVC/H.265` 和 `AV1` 编码格式视频

# **TODO**
- [X] **视频类**
  - [X] 用户投稿视频 (含分P, 合集视频)
- [X] **番组类**
  - [X] 番剧
  - [X] 电影
  - [X] 纪录片
  - [X] 国创
  - [X] 综艺
  - [X] 电视剧
- [X] **音乐类**
  - [X] 音乐
  - [X] 歌单
- [X] **直播**
- [ ] **课程**
- [ ] **漫画**
- [ ] **专栏**
- [X] **其他**
  - [X] 账号登录
  - [X] 下载弹幕
  - [X] 下载字幕
  - [X] 下载歌词

# 更新日志
### **Version 1.33 (2022-12-2)**
本次更新内容如下：
* 支持代理身份验证
* 修复代理 https 有关问题
* 修复部分已知问题

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: https://scott.o5g.top
