# Bili23-Downloader ![Version](https://img.shields.io/github/v/release/ScottSloan/Bili23-Downloader?style=flat-square) ![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square) ![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ScottSloan/Bili23-Downloader/Build?style=flat-square)
 
下载 Bilibili 视频/番剧/电影/纪录片 等资源  

+ [下载地址](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [常见问题](https://github.com/ScottSloan/Bili23-Downloader/blob/main/issues.md)
+ [开发日志](#开发日志) 
+ [联系方式](#联系方式)

# 使用说明
### **安装**
```bash
# 克隆仓库
git clone https://github.com/ScottSloan/Bili23-Downloader.git

# 安装所需依赖
cd Bili23-Downloader
pip install -r requirements.txt
```

- **本程序需要使用 `ffmpeg` 合成视频，请将 `ffmpeg.exe` 放置到程序运行目录下 ([下载地址](http://www.ffmpeg.org/download.html))**
- **[Github Actions](https://github.com/ScottSloan/Bili23-Downloader/actions) 中提供已经打包完成的程序，可直接运行 (不包含 ffmpeg)**

### **主界面**
![main.PNG](https://s2.loli.net/2022/04/09/pdlOtZ28yf5F4nU.png)  
将视频链接粘贴到地址栏中，点击 `Get` 按钮解析视频链接  
选择要下载的视频，点击 `下载视频` 按钮开始下载 

#### **支持输入的 URL 链接**
- 用户投稿类型视频链接
- 剧集（番剧，电影，纪录片等）链接
- 活动页链接
- 直播链接
- 音乐链接
- b23.tv 短链接

#### **部分视频可直接输入编号**
- 视频 av、BV 号
- 剧集 epid、md、ss 号

### **下载管理界面**
![download.PNG](https://s2.loli.net/2022/04/09/Z2p9cEJsuwqCoAI.png)  
下载的视频以 `视频名称.mp4` 命名，关闭程序后未完成的任务需重新下载
> 目前暂不支持断点续传功能

### **其他功能**
- 支持显示完整剧集列表，如 PV，看点，特别企划等  
- 下载弹幕 (仅支持下载为 `xml` 格式，`ass` 和 `proto` 格式后续支持)  
- 下载字幕 (下载为 `srt` 格式，如果视频有多个字幕将全部下载)  
- 下载歌词 (下载为 `lrc` 格式)
- 支持网络代理  
- 支持下载 `AVC/H.264`，`HEVC/H.265` 和 `AV1` 编码格式视频

### **添加 Cookie**
![cookie.png](https://s2.loli.net/2022/04/09/caH5VFbSzRM6mwK.png)  
浏览器登录B站，按下 F12 键打开开发者工具，选择 `应用` 选项卡 -> Cookie，找到 `SESSDATA` 字段，在程序设置中添加即可  
![login.png](https://s2.loli.net/2022/04/17/ngkDbtFdAxevpHa.png)  
你也可以点击 `扫码登录` 按钮，自动获取 Cookie 并填入 
> Cookie 有效期为一个月，请定期更新

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
#### **[最新] Version 1.21 dev (2022-4-30)**
- 优化了登录功能
- 优化部分细节效果
- 修复视频信息预览页面显示问题

<details>
<summary>Version 1.20</summary>

#### **Version 1.20 (2022-4-22)**

* 重写下载功能相关代码，并加入下载管理窗口
* 新增支持下载 AV1 编码的视频
* 支持解析音乐链接，可下载歌词
* 支持扫码登录，一键获取 Cookie
* 修复部分已知问题

</details>

<details>
<summary>Version 1.14</summary>

#### **Version 1.14 (2022-4-3)**
- 支持字幕文件下载和自动添加字幕功能
- 支持下载 AVC/H.264 和 HEVC/H.265 编码的视频
- 支持活动页链接解析
- 支持直播链接解析，可使用播放器播放
- 支持使用代理下载视频
- 彻底修复了视频不能下载的问题

</details>

<details>
<summary>Version 1.13</summary>

#### **Version 1.13 (2022-3-13)**
- 番组现已支持 番剧/电影/纪录片/综艺/国创/电视剧 类型的下载
- 现在合集视频能够显示完整列表
- 添加了"设置"功能
- 优化了部分细节效果
- 修正了部分已知问题

</details>

<details>
<summary>Version 1.12</summary>

#### **Version 1.12 (2022-2-20)**
- 程序初始版本发布
- 可下载B站的视频和番剧，方便离线观看

</details>

## 联系方式
- Email: World1019@sina.com
- Blog: https://scott.hanloth.cn
