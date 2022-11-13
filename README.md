# Bili23-Downloader
![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.9.12-green?style=flat-square) ![wxPython](https://img.shields.io/badge/wxPython-4.2.0-green?style=flat-square) ![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)

下载 Bilibili 视频/番剧/电影/纪录片 等资源  

+ [下载地址](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [常见问题](https://github.com/ScottSloan/Bili23-Downloader/blob/main/issues.md)
+ [开发日志](#开发日志) 
+ [联系方式](#联系方式)

### Bili23 Downloader 系列
* GUI 桌面端版本
* [CLI 命令行版本](https://github.com/ScottSloan/Bili23-Downloader-CLI)

# 使用说明
### **安装**
```bash
# 克隆仓库
git clone https://github.com/ScottSloan/Bili23-Downloader
cd Bili23-Downloader

# 为提高下载速度，建议更换 pip 国内源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装所需依赖
pip install -r requirements.txt
```

- **本程序需要使用 `ffmpeg` 合成视频，请将 `ffmpeg.exe` 放置到程序运行目录下 ([下载地址](http://www.ffmpeg.org/download.html))**
- **[Github Actions](https://github.com/ScottSloan/Bili23-Downloader/actions) 中提供已经打包完成的程序，可直接运行 (不包含 ffmpeg)**

### **主界面**
![main.png](https://s2.loli.net/2022/05/01/AMiCgvUKlzbpjY3.png)  
将视频链接粘贴到地址栏中，点击 `Get` 按钮解析视频链接  
选择要下载的视频，点击 `下载视频` 按钮开始下载 

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

### **下载管理界面**
![download.PNG](https://s2.loli.net/2022/04/09/Z2p9cEJsuwqCoAI.png)  
下载的视频以 `视频名称.mp4` 命名，关闭程序后未完成的任务需重新下载
> 目前暂不支持断点续传功能

### **用户中心界面**
![user.png](https://s2.loli.net/2022/05/01/k6hAztIUqny4M8s.png)  

目前可通过客户端扫描二维码登录，登录后可下载大会员视频  
> **每次登录有效期为一个月，过期后需重新登录**

### **其他功能**
- 支持显示完整剧集列表，如 PV，看点，特别企划等  
- 下载弹幕 (仅支持下载为 `xml` 格式，`ass` 和 `proto` 格式后续支持)  
- 下载字幕 (下载为 `srt` 格式，如果视频有多个字幕将全部下载)  
- 下载歌词 (下载为 `lrc` 格式)
- 支持网络代理  
- 支持下载 `AVC/H.264`，`HEVC/H.265` 和 `AV1` 编码格式视频

# 常见问题
[常见问题](https://github.com/ScottSloan/Bili23-Downloader/blob/main/issues.md)

# TODO
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
- [ ] **其他**
  - [X] 账号登录
  - [ ] 下载弹幕
    - [X] xml 格式
    - [ ] ass 格式
    - [ ] proto 格式
  - [X] 下载字幕
  - [X] 检查更新

# 开发日志
## 目前项目正在进行重构 (2022-10-18)
#### **[最新] Version 1.22 dev (2022-5-8)**
* 支持解析歌单链接

#### **Version 1.21 (2022-5-8)**
* 使用 `aria2` 实现下载功能
* 现在任务栏上能显示当前下载状态
* 优化部分细节效果
* 修复视频信息预览页面显示问题
* 修复其他问题

# 联系方式
- Email: scottsloan@petalmail.com
- Blog: https://scott.o5g.top
