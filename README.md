# Bili23-Downloader
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.9.12-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.0-green?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat)


Bili23 Downloader GUI 桌面端版本

下载 Bilibili 视频/番剧/电影/纪录片 等资源  

+ [下载地址](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [TODO](#todo)
+ [更新日志](#更新日志) 
+ [联系方式](#联系方式)

### **Bili23 Downloader 系列**
* GUI 桌面端版本 (本项目)
* [CLI 命令行版本](https://github.com/ScottSloan/Bili23-Downloader-CLI)

# 使用说明
### **安装主程序**

请前往 [Release](https://github.com/ScottSloan/Bili23-Downloader/releases) 页面，下载最新版本。

### **安装 ffmpeg**
由于 `dash` 格式视频依赖 `ffmpeg` 进行合成，需事先安装

### **Windows 用户请按照下面的步骤安装** 
ffmpeg 下载地址：[蓝奏云](https://wwf.lanzout.com/iTYX00ft3u4h)  密码:h9ge  

解压压缩包，记录 `ffmpeg` 所在文件夹的路径，按照以下步骤创建环境变量：

> 此电脑 -> 右键 -> 属性 -> 高级系统设置 -> 环境变量 -> 系统变量 -> Path -> 编辑 -> 新建 -> ffmpeg 所在文件夹的路径

详细步骤请看[这里](https://scott.o5g.top/index.php/archives/120/)

### **Linux 用户请执行以下命令安装**

```
sudo apt install ffmpeg
```


### **主界面**
![main.png](https://s2.loli.net/2022/05/01/AMiCgvUKlzbpjY3.png)  
将视频链接粘贴到地址栏中，点击 `Get` 按钮解析视频链接  
选择要下载的视频，点击 `下载视频` 按钮开始下载 

#### **支持输入的 URL 链接**
- 用户投稿类型视频链接
- 番组（番剧，电影，纪录片等）链接
- 活动页链接
- 直播链接
- 音乐、歌单链接
- b23.tv 短链接

#### **部分类型可直接输入编号**
- 视频 av、BV 号
- 剧集 epid、md、ss 号
- 音乐 au 号、歌单 am 号

### **下载管理**
![download.PNG](https://s2.loli.net/2022/04/09/Z2p9cEJsuwqCoAI.png) 

下载功能使用流式下载实现，大幅提升下载速度，经测试可跑满带宽。

> 关闭程序后未完成的任务需重新开始下载

### **用户中心**
![user.png](https://s2.loli.net/2022/05/01/k6hAztIUqny4M8s.png)  

目前可通过客户端扫描二维码登录，登录后可下载大会员视频  
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
### **Version 1.30 b0 (2022-11-24)**
时隔 6 个月，Bili23 Downloader 迎来 Version 1.30 更新！

本次更新内容如下：
* 完全重构项目，去除冗杂代码，提升运行效率
* 优化窗口在高 DPI 下的显示效果
* 程序主界面可展示用户名称头像等信息
* 登录界面二维码自动刷新
* 修复检查更新接口无效的问题
* 修复路径含有空格时无法合成视频的问题
* 支持调试功能
* 支持 Linux 平台
* 移除视频信息查看功能
* 其它未列出的诸多优化

ffmpeg 安装更加简便，现已提供高速下载链接，以及简明的安装教程。
同时提供编译版的程序，无需安装相关依赖，独立运行，点开即用。

从 V1.30 开始，Bili23 Downloader 将分为 CLI 命令行版本和 GUI 桌面端版本
两个项目并行开发，继续延续简便易用的设计理念，为用户带来最佳的体验。

另外，本项目的开发并未停止，它将继续进行下去，未来将上线更多实用功能。

感谢大家的支持！

### **Version 1.30 b1 (2022-11-24)**
本次更新内容如下：
* 修复本地化问题
* 修复登录有效期判断问题
* 修复剧集列表显示问题
* 修复无法保存设置的问题
* 其它细节优化

### **Version 1.30 b2 (2022-11-25)**
本次更新内容如下：
* 重新加入直播和音乐链接解析功能
* 增加更多错误提示
* 修复配置文件问题
* 修复下载列表显示问题
* 修复下载路径问题
* 修正说明文档中的错误
* 其它细节优化

# 联系方式
- Email: scottsloan@petalmail.com
- Blog: https://scott.o5g.top
