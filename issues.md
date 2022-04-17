# 常见问题
### Q：不能获取视频信息？
#### A：请在设置中添加大会员 Cookie，如果依然报错，请提交 issue，附上视频链接
**添加 Cookie 方法**  
![cookie.png](https://s2.loli.net/2022/04/09/caH5VFbSzRM6mwK.png)  
浏览器登录B站，按下 F12 键打开开发者工具，选择 `应用` 选项卡 -> Cookie，找到 `SESSDATA` 字段，在程序设置中添加即可  

![login.png](https://s2.loli.net/2022/04/17/ngkDbtFdAxevpHa.png)  
你也可以点击 `扫码登录` 按钮，自动获取 Cookie 并填入
> Cookie 有效期为一个月，请定期更换

#
### Q：视频一直处于 "等待下载" 状态？
#### A：如果是视频比较大 (超过 1GB)，至少要等待半分钟才会开始下载，这个问题后续会修复。

#
### Q：视频下载很慢？
#### A：B 站服务器处于高峰期状态，隔一段时间再来下载吧

#
### Q：视频不能合成？
#### A：请确保已经安装 ffmpeg，如果未安装，请下载 ffmpeg，将 ffmpeg.exe 放置到程序运行目录下 ([下载地址](http://www.ffmpeg.org/download.html))

#
### Q：下载的视频不能播放？
#### A：可能是设备不支持 HEVC/H.265 或 AV1 编码，在设置中将视频编码选项切换为 AVC/H.264 后，重新下载即可。
