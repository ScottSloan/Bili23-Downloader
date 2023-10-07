# Bili23-Downloader-GUI
![Github](https://img.shields.io/badge/GitHub-black?logo=github&style=flat) ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat) ![Python](https://img.shields.io/badge/Python-3.11.5-green?style=flat) ![wxPython](https://img.shields.io/badge/wxPython-4.2.1-green?style=flat) ![License](https://img.shields.io/badge/license-MIT-orange?style=flat)

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
[![pPb0AS0.png](https://z1.ax1x.com/2023/09/28/pPb0AS0.png)](https://imgse.com/i/pPb0AS0)

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
[![pP78HaT.png](https://z1.ax1x.com/2023/09/25/pP78HaT.png)](https://imgse.com/i/pP78HaT) 

### **登录**
由于B站限制，未登录状态下只能获取到 `480P` 视频，因此建议您扫码登录后使用。

> 登录有效期为半年，过期后需重新登录。

# 更新日志
### **Version 1.40 (2023/10/06)**
Bili23 Downloader 1.40 版本发布

迟来的更新。

本次更新内容：
* 新版下载管理器上线，支持并行下载，在下载管理页面中即可快速设置，即时生效，且下载任务可一键暂停，一键恢复
* 新增下载任务略缩图显示功能
* 增强活动页链接识别能力
* 修正视频无法下载的问题 (文件大小显示为 18 字节)
* 修正视频无法合成的问题
* 修正无法覆盖下载的问题
* 修正代理身份验证无法使用的问题
* 修正部分视频标题显示异常的问题
* 调整用户信息保存策略，现在程序仅获取用户名称、头像以及 SESSDATA
* 调整检查更新接口，提升访问速度
* 优化了下载逻辑，现在暂停任务后恢复下载不会导致下载速度变慢
* 优化了程序关于页面
* 移除了音乐、歌单以及直播的解析下载功能
* 移除了用户中心
* 暂时移除了弹幕、字幕、歌词下载功能，下个版本将优化相关下载体验

关于并行下载的说明：
目前并行下载功能最多支持设置 4 个，但程序并不严格限制，您也可手动点击 '开始下载' 按钮同时下载更多的视频。

目前未登录情况下只能获取到 480P 的清晰度，因此建议您扫码登录后再下载视频。  
个人博客已重新上线，后续有关 Bili23 Downloader 的开发动态会在上面发布，也欢迎提出意见或指出问题，感谢大家的支持！  
Bili23 Downloader CLI 的新版本将会在后续推出。

**此次更新为 Beta 版本，暂不提供编译版本下载，详细安装教程请点击[这里](https://scott-sloan.cn/archives/12/)。**

# 联系方式
- QQ: 2592111619
- Email: scottsloan@petalmail.com
- Blog: [沧笙踏歌](https://scott-sloan.cn)
