# Bili23-Downloader
![](https://img.shields.io/badge/Latest_Version-1.14-green.svg) ![](https://img.shields.io/badge/Python-3.8.10-green.svg) ![Build](https://github.com/ScottSloan/Bili23-Downloader/actions/workflows/build.yml/badge.svg)
 
下载 Bilibili 视频/番剧/电影/纪录片 等资源  

+ [下载链接](https://github.com/ScottSloan/Bili23-Downloader/releases)
+ [使用说明](#使用说明)
+ [安装](#安装)
+ [TODO](#to-do)
+ [开发日志](#开发日志)
# 声明
#### **本程序仅供学习交流使用，请勿用于商业用途。**  
# 使用说明
### **主界面**
![main.PNG](https://s2.loli.net/2022/04/09/pdlOtZ28yf5F4nU.png)
将视频链接粘贴到地址栏中，点击 `Get` 按钮解析视频链接  
选择要下载的视频，点击 `下载视频` 按钮开始下载
#### **支持输入的 URL 链接**
- 用户投稿类型视频链接
- 剧集（番剧，电影，纪录片等）链接
- 活动页链接
- 直播链接
- b23.tv 短链接
#### **部分视频可直接输入编号**
- 视频 av 或 BV 号
- 剧集 epid 或 md（media_id） 或 ss（season_id） 号
### **下载管理界面**
![download.PNG](https://s2.loli.net/2022/04/09/Z2p9cEJsuwqCoAI.png)
> 目前暂不支持断点续传功能
### **其他功能**
- 显示完整剧集列表，如 PV，看点，特别企划等
- 下载弹幕 (仅支持下载为 `xml` 格式，`ass` 和 `proto` 格式后续支持)
- 下载字幕 (下载为 `srt` 格式，如果视频有多个字幕将全部下载)
- 支持网络代理 (`https`)

### **添加 Cookie**
![cookie.png](https://s2.loli.net/2022/04/09/caH5VFbSzRM6mwK.png)
浏览器登录B站，按下 F12 键打开开发者工具，选择 `应用程序` 选项卡 -> Cookie，找到 `SESSDATA` 字段，在程序设置中添加即可 
> Cookie 有效期为一个月，请定期更换
# 安装
- **克隆仓库**
```
git clone https://github.com/ScottSloan/Bili23-Downloader.git
```
- **安装程序所需依赖**
```
pip install -r requirements.txt
```
- **打包为独立程序**
```
# 安装 pyinstaller
pip intall pyinstaller

# 运行 pyinstaller 打包程序
pyinstaller -F -w GUI.py --dist ./ --add-data "pic;pic" --add-data "info;info"
```
- **本项目每周自动构建一次，如需下载打包后的版本，请到 [Github Actions](https://github.com/ScottSloan/Bili23-Downloader/actions) 中下载**
- **注：`ffmpeg` 需手动下载安装，请将 `ffmpeg.exe` 放置到程序运行目录下 ([下载地址](http://www.ffmpeg.org/download.html))**

# TODO
- [X] **视频类**
  - [X] 用户投稿视频 (分P,合集)
- [X] **番组类**
  - [X] 番剧
  - [X] 电影
  - [X] 纪录片
  - [X] 国创
  - [X] 综艺
  - [X] 电视剧
- [X] **直播**
- [ ] **漫画**
- [ ] **专栏**
- [ ] **其他**
  - [ ] 下载弹幕
    - [X] xml 格式
    - [ ] ass 格式
    - [ ] proto 格式
  - [X] 下载字幕
  - [X] 检查更新
# 开发日志
#### **[最新] 版本 1.20 dev (2022-4-9)**
- 重写下载功能相关代码，并加入下载管理窗口
- 新增支持下载 AV1 编码的视频
- 修复部分已知问题
#### **版本 1.14 (2022-4-3)**
- 支持字幕文件下载和自动添加字幕功能
- 支持下载 AVC/H.264 和 HEVC/H.265 编码的视频
- 支持活动页链接解析
- 支持直播链接解析，可使用播放器播放
- 支持使用代理下载视频
- 彻底修复了视频不能下载的问题
#### **版本 1.13 (2022-3-13)**
- 番组现已支持 番剧/电影/纪录片/综艺/国创/电视剧 类型的下载
- 现在合集视频能够显示完整列表
- 添加了"设置"功能
- 优化了部分细节效果
- 修正了部分已知问题
#### **版本 1.12 (2022-2-20)**
- 程序初始版本发布
- 可下载B站的视频和番剧，方便离线观看
## 总结
- **如果这个项目有帮助到您，可以点个 Star，感谢支持！**
