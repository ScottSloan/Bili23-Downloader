# yt-dlp 下载器集成指南

## 概述

本指南介绍如何在 Bili23 项目中集成和使用基于 yt-dlp 的下载模块。该模块提供了与现有项目架构完全兼容的下载解决方案。

## 文件结构

```
src/util/download/
├── yt_dlp_downloader.py     # 核心下载器
├── yt_dlp_adapter.py        # 任务适配器
└── yt_dlp_integration.py    # GUI 集成示例
```

## 核心功能

### 1. 基础下载器 (YTDLPDownloader)

**主要特性：**
- 单任务下载支持
- 进度回调（支持 GUI 集成）
- 错误处理和重试机制
- Cookie 支持（B站强烈建议）
- 可扩展配置
- Qt 信号机制兼容

**基本用法：**

```python
from util.download.yt_dlp_downloader import YTDLPDownloader

downloader = YTDLPDownloader()

# 连接信号
downloader.progress_signal.connect(on_progress)
downloader.finished_signal.connect(on_finished)
downloader.error_signal.connect(on_error)

# 开始下载
downloader.download(
    url="https://www.bilibili.com/video/BV1xxx",
    output_dir="./downloads",
    cookie_file="cookies.txt"  # 可选
)
```

### 2. 任务适配器 (YTDLPTaskAdapter)

**与现有 TaskInfo 系统集成：**

```python
from util.download.yt_dlp_adapter import YTDLPTaskAdapter

adapter = YTDLPTaskAdapter()

# 连接任务信号
adapter.task_progress_signal.connect(on_task_progress)
adapter.task_finished_signal.connect(on_task_finished)
adapter.task_error_signal.connect(on_task_error)

# 开始下载任务
adapter.start_download(task_info)
```

### 3. GUI 集成 (YTDLPGUIHandler)

**与现有 GUI 组件集成：**

```python
from util.download.yt_dlp_integration import YTDLPGUIHandler

handler = YTDLPGUIHandler(parent_widget)

# 连接 GUI 信号
handler.download_started.connect(on_download_started)
handler.download_progress.connect(on_download_progress)
handler.download_finished.connect(on_download_finished)
handler.download_error.connect(on_download_error)

# 开始下载
handler.start_download(url, output_dir, cookie_file)
```

## 集成步骤

### 步骤 1: 安装依赖

已自动更新 `requirements.txt` 和 `pyproject.toml`，包含：

```
yt-dlp==2024.11.15
```

运行安装：
```bash
pip install -r requirements.txt
```

### 步骤 2: 替换现有下载器（可选）

#### 方法 A: 完全替换

在现有的下载管理器中使用 yt-dlp 下载器：

```python
# 在现有的下载管理器中
from util.download.yt_dlp_adapter import get_global_adapter

class DownloadManager:
    def __init__(self):
        self.yt_dlp_adapter = get_global_adapter()
        self._connect_signals()
    
    def _connect_signals(self):
        self.yt_dlp_adapter.task_progress_signal.connect(self._on_progress)
        self.yt_dlp_adapter.task_finished_signal.connect(self._on_finished)
        self.yt_dlp_adapter.task_error_signal.connect(self._on_error)
    
    def start_download(self, task_info):
        return self.yt_dlp_adapter.start_download(task_info)
```

#### 方法 B: 混合使用

作为备用下载器，当现有下载器失败时使用：

```python
def download_with_fallback(self, task_info):
    # 先尝试现有下载器
    if self.existing_downloader.download(task_info):
        return True
    
    # 失败时使用 yt-dlp
    logger.warning("主下载器失败，切换到 yt-dlp")
    return self.yt_dlp_adapter.start_download(task_info)
```

### 步骤 3: GUI 集成

在现有的 GUI 组件中集成进度显示：

```python
# 在现有的下载列表组件中
class DownloadListItem(QWidget):
    def __init__(self, task_info):
        super().__init__()
        self.task_info = task_info
        self._setup_progress_display()
    
    def _setup_progress_display(self):
        # 连接 yt-dlp 进度信号
        from util.download.yt_dlp_adapter import get_global_adapter
        adapter = get_global_adapter()
        adapter.task_progress_signal.connect(self._update_progress)
    
    def _update_progress(self, task_info, progress_data):
        if task_info == self.task_info:
            # 更新进度条和状态显示
            self.progress_bar.setValue(progress_data.get('percent', 0))
            self.speed_label.setText(progress_data.get('speed', ''))
```

## 配置选项

### 默认配置

```python
from util.download.yt_dlp_downloader import YTDLPDownloader

config = YTDLPDownloader.get_default_config()
print(config)
# {
#     'format': 'bv+ba/b',
#     'merge_output_format': 'mp4',
#     'retries': 3,
#     'concurrent_fragment_downloads': 4,
#     'quiet': True,
#     'no_warnings': True,
# }
```

### 自定义配置

```python
custom_config = YTDLPDownloader.create_custom_config(
    format="bestaudio/best",      # 只下载音频
    ratelimit=1024 * 1024,        # 限速 1MB/s
    proxy="http://127.0.0.1:7890", # 代理
    extract_flat=True             # 不下载，只获取信息
)
```

## 高级功能

### 批量下载

```python
urls = [
    "https://www.bilibili.com/video/BV1xxx",
    "https://www.bilibili.com/video/BV2xxx",
]

for url in urls:
    downloader.download(url)
```

### Cookie 支持

```python
# 从配置文件读取 cookie
cookie_file = config.get(config.cookie_file)
if cookie_file:
    downloader.download(url, cookie_file=cookie_file)
```

### 错误处理

```python
def on_error(error_msg):
    if "会员专享" in error_msg:
        logger.warning("需要会员才能下载")
        # 提示用户登录或使用 cookie
    elif "404" in error_msg:
        logger.error("视频不存在")
    else:
        logger.error(f"下载错误: {error_msg}")
```

## 测试

运行测试脚本验证功能：

```bash
python test_yt_dlp.py
```

## 注意事项

### 线程安全
- yt-dlp 下载器使用 Qt 线程池，确保线程安全
- 所有 GUI 更新通过信号机制，避免直接操作 UI

### 性能考虑
- 单任务下载模式，避免资源竞争
- 可配置并发下载片段数量
- 支持速度限制

### 兼容性
- 与现有 PySide6 架构完全兼容
- 使用相同的信号机制
- 支持现有的 TaskInfo 数据结构

## 故障排除

### 常见问题

1. **导入错误**：检查 `requirements.txt` 是否已更新
2. **下载失败**：检查网络连接和 cookie 文件
3. **GUI 卡顿**：确保使用信号机制，避免阻塞 UI 线程

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展开发

### 添加新功能

在 `yt_dlp_downloader.py` 中添加新配置选项：

```python
def enable_advanced_features(self):
    self.ydl_opts.update({
        "writeinfojson": True,      # 保存信息文件
        "writethumbnail": True,     # 下载缩略图
        "embedthumbnail": True,     # 嵌入缩略图
    })
```

### 自定义回调

扩展进度回调处理：

```python
def _hook(self, d):
    # 调用父类处理
    super()._hook(d)
    
    # 添加自定义处理
    if d.get("status") == "downloading":
        # 自定义进度处理
        self.custom_progress_callback(d)
```

## 总结

这个 yt-dlp 下载模块提供了：

- ✅ 与现有项目架构完全兼容
- ✅ 完整的进度回调支持
- ✅ 错误处理和重试机制
- ✅ Cookie 和代理支持
- ✅ 可扩展的配置系统
- ✅ Qt 信号机制集成
- ✅ 线程安全的实现

通过简单的集成步骤，你可以快速将 yt-dlp 的强大功能添加到你的 Bili23 项目中。