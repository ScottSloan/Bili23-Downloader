## 1.60.0 (2025-03-17)
### 新增
* 支持编辑框三击全选 by @IvanHanloth (#77)
* 支持自定义下载文件名 by @ScottSloan
* 支持截取视频/音频片段 by @ScottSloan (#78)
* 支持独立设置下载出错重试和自动重启下载选项 by @ScottSloan
* 下载页面调整为"正在下载"和"下载完成"两个分页 by @ScottSloan

### 优化
* 优化下载模块，避免文件写入冲突 by @ScottSloan
* 优化出错重试逻辑 by @ScottSloan (#81)
* 优化重名文件覆盖逻辑 by @ScottSloan (#84)
* 优化主页链接框显示效果，支持一键清空 by @ScottSloan
* 优化读取大量断点续传文件时的启动速度 by @ScottSloan
* 优化剧集列表自动勾选逻辑 by @ScottSloan (#90)
* 优化弹幕、字幕和封面文件下载体验 by @ScottSloan

### 修复
* 修复异常显示下载完成的情况 by @ScottSloan (#82)
* 修复部分情况下载失败的问题 by @ScottSloan (#66)
* 修复下载后音视频残缺的问题 by @ScottSloan (#87)
* 修复部分情况下无法下载弹幕、字幕和封面文件的问题 by @ScottSloan (#89)