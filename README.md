# Bili23-Downloader
![](https://img.shields.io/badge/Latest_Version-1.13-green.svg) ![](https://img.shields.io/badge/Python-3.8.10-green.svg) ![](https://img.shields.io/badge/wxPython-4.1.1-green.svg)  
  
下载 Bilibili 视频/番剧/电影/纪录片 等资源  
## 声明
#### 本程序仅供学习交流使用，请勿用于商业用途。  
## 功能介绍
- **支持输入的 URL 链接**
> - 用户投稿类型视频链接
> - 剧集（番剧，电影，纪录片等）链接
> - b23.tv 短链接
> - 部分视频可直接输入编号：
> > - 视频 av 或 BV 号
> > - 剧集 epid 或 md（media_id） 或 ss（season_id） 号
- **支持 GUI 图形界面**  
> - 显示剧集列表，可勾选需要下载的部分
> - 显示视频相关信息（封面，播放数，三连数等）
- **支持下载弹幕和字幕**  
> - 弹幕目前仅支持下载 xml 格式，后续会支持 ass，proto 等格式
> - 下载 srt 格式字幕
> - 自动添加字幕
- **支持自定义清晰度下载**  
> - 可自定义清晰度（取决于视频所支持的清晰度）  
> - 免登录下载 `1080P` 视频  
> - **注：`1080P+` 及以上清晰度需要使用大会员 Cookie 才能下载。**
## 安装
- **克隆仓库**
```
git clone https://github.com/ScottSloan/Bili23-Downloader.git
```
- **安装程序所需依赖**
```
pip install -r requirements.txt
```
- **请注意，ffmpeg 需手动下载安装，请将 ffmpeg.exe 放置到程序运行目录下 (GUI.py 同级目录)**
## 运行截图
> - 主界面
> > - ![main.png](https://s2.loli.net/2022/03/13/mbf4WduIlViO19q.png)
> - 查看番剧信息
> > - ![info.png](https://s2.loli.net/2022/03/13/9Vpaol6DZzmwn54.png)
> - 下载完成
> > - ![play.png](https://s2.loli.net/2022/03/13/C4zOUAiX3aWnYMv.png)
## 添加 Cookie
- **适用于需要使用大会员 Cookie 才能下载的情况**
> - 添加方法：浏览器登录B站，按下 F12 键打开开发者工具，选择 应用(application) 选项卡 -> cookie，找到 SESSDATA 字段，复制粘贴即可。
> - **注：Cookie 有效期为一个月，请定期更换。**
## TO-DO
- [X] **视频类**
  - [X] 用户投稿视频 (分P,合集)
- [X] **番组类**
  - [X] 番剧
  - [X] 电影
  - [X] 纪录片
  - [X] 国创
  - [X] 综艺
  - [X] 电视剧
- [ ] **小视频**
- [ ] **直播**
- [ ] **漫画**
- [ ] **其他**
  - [ ] 下载弹幕
    - [X] xml 格式
    - [ ] ass 格式
    - [ ] proto 格式
  - [X] 下载字幕
  - [X] 检查更新
## 开发日志
- **正在考虑重写下载功能(多任务下载)**
- **[最新] 版本 1.14 alpha (2022-3-20)**
> - 支持字幕文件下载和自动添加字幕功能
> - 修复了部分视频不能下载的问题
- **版本 1.13 (2022-3-13)**
> - 番组现已支持 番剧/电影/纪录片/综艺/国创/电视剧 类型的下载
> - 现在合集视频能够显示完整列表
> - 添加了"设置"功能
> - 优化了部分细节效果
> - 修正了部分已知问题
- **版本 1.12 (2022-2-20)**
> - 程序初始版本发布
> - 可下载B站的视频和番剧，方便离线观看
## 总结
- **如果这个项目有帮助到您，可以点个 Star，感谢支持！**
