# yt-dlp 升级集成指南

## 概述

本次升级为 yt-dlp 下载模块添加了完整的任务管理系统，实现了正确的架构分层：

```
UI → TaskManager → ControlledDownloader
```

## 架构说明

### ❌ 错误的架构（之前）
```
UI → Downloader
```

### ✅ 正确的架构（现在）
```
UI → YTDLPUIDelegate → TaskManager → ControlledDownloader
```

## 核心组件

### 1. 任务状态机 (TaskStatus)

定义任务的所有可能状态：

```python
class TaskStatus(Enum):
    WAITING = "waiting"        # 等待中
    DOWNLOADING = "downloading" # 下载中
    FINISHED = "finished"      # 已完成
    FAILED = "failed"          # 失败
    PAUSED = "paused"          # 暂停
    CANCELLED = "cancelled"    # 已取消
    RETRYING = "retrying"      # 重试中
```

### 2. 下载任务 (DownloadTask)

数据类，包含任务的所有信息：

```python
@dataclass
class DownloadTask:
    url: str                      # 视频URL
    output_dir: str               # 输出目录
    task_id: str                  # 任务ID（自动生成）
    title: str                    # 视频标题
    cookie_file: Optional[str]    # Cookie文件
    status: TaskStatus            # 任务状态
    priority: TaskPriority        # 优先级
    progress: float               # 进度
    speed: str                    # 速度
    eta: str                      # 预计剩余时间
    retry_count: int              # 重试次数
    max_retries: int              # 最大重试次数
    # ... 更多字段
```

### 3. 受控下载器 (ControlledDownloader)

支持 start/stop/retry 操作的下载器：

```python
class ControlledDownloader:
    def __init__(self, task: DownloadTask):
        self.task = task
        self._stop_event = threading.Event()
    
    def start(self, progress_callback, finish_callback, error_callback) -> bool:
        """开始下载"""
        pass
    
    def stop(self) -> bool:
        """停止下载"""
        pass
    
    def retry(self, progress_callback, finish_callback, error_callback) -> bool:
        """重试下载"""
        pass
```

### 4. 任务管理器 (TaskManager)

管理下载任务队列：

```python
class TaskManager:
    def __init__(self, max_concurrent: int = 1):
        self.queue = []              # 任务队列
        self.current = None          # 当前任务
        self.current_downloader = None  # 当前下载器
        self.finished_tasks = []     # 已完成任务
        self.failed_tasks = []       # 失败任务
    
    def add_task(self, task: DownloadTask) -> str:
        """添加任务到队列"""
        pass
    
    def start_next(self) -> bool:
        """开始下一个任务"""
        pass
    
    def stop_current(self) -> bool:
        """停止当前任务"""
        pass
    
    def retry_task(self, task_id: str) -> bool:
        """重试指定任务"""
        pass
    
    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        pass
```

### 5. UI 代理 (YTDLPUIDelegate)

UI 和 TaskManager 之间的桥梁：

```python
class YTDLPUIDelegate(QObject):
    # UI 信号
    task_added_signal = Signal(object)
    task_progress_signal = Signal(object, dict)
    task_finished_signal = Signal(object)
    task_failed_signal = Signal(object, str)
    
    def add_task(self, url, output_dir, title, cookie_file, priority, config) -> str:
        """添加下载任务"""
        pass
    
    def start_download(self) -> bool:
        """开始下载"""
        pass
    
    def stop_download(self) -> bool:
        """停止下载"""
        pass
```

## 使用示例

### 基础使用

```python
from util.download.task_manager import (
    TaskManager, 
    DownloadTask, 
    TaskStatus, 
    TaskPriority
)

# 创建任务管理器
manager = TaskManager(max_concurrent=1)

# 设置回调
def on_progress(task, data):
    print(f"任务 {task.task_id} 进度: {data.get('percent')}")

def on_finish(task):
    print(f"任务 {task.task_id} 完成")

def on_error(task, error_msg):
    print(f"任务 {task.task_id} 失败: {error_msg}")

manager.set_callbacks(
    progress=on_progress,
    finish=on_finish,
    error=on_error
)

# 添加任务
task1 = DownloadTask(
    url="https://www.bilibili.com/video/BV1xxx",
    output_dir="./downloads",
    title="视频1",
    priority=TaskPriority.NORMAL
)

task2 = DownloadTask(
    url="https://www.bilibili.com/video/BV2xxx",
    output_dir="./downloads",
    title="视频2",
    priority=TaskPriority.HIGH
)

manager.add_task(task1)
manager.add_task(task2)

# 开始下载
manager.start_next()
```

### GUI 集成

```python
from util.download.yt_dlp_ui_delegate import YTDLPUIDelegate

# 创建 UI 代理
delegate = YTDLPUIDelegate(parent=self)

# 连接信号
delegate.task_added_signal.connect(self.on_task_added)
delegate.task_progress_signal.connect(self.on_task_progress)
delegate.task_finished_signal.connect(self.on_task_finished)
delegate.task_failed_signal.connect(self.on_task_failed)

# 添加任务
task_id = delegate.add_task(
    url="https://www.bilibili.com/video/BV1xxx",
    output_dir="./downloads",
    title="视频标题",
    cookie_file="cookies.txt"
)

# 开始下载
delegate.start_download()

# 停止下载
delegate.stop_download()

# 重试任务
delegate.retry_task(task_id)

# 取消任务
delegate.cancel_task(task_id)
```

### 批量下载

```python
# 添加多个任务
urls = [
    "https://www.bilibili.com/video/BV1xxx",
    "https://www.bilibili.com/video/BV2xxx",
    "https://www.bilibili.com/video/BV3xxx",
]

for url in urls:
    delegate.add_task(url=url, output_dir="./downloads")

# 自动开始下载（第一个任务）
delegate.start_download()

# 后续任务会自动开始
```

### 任务控制

```python
# 获取任务信息
task = delegate.get_task(task_id)
print(f"状态: {task.status}")
print(f"进度: {task.progress}%")
print(f"速度: {task.speed}")

# 获取队列状态
status = delegate.get_queue_status()
print(f"队列长度: {status['queue_length']}")
print(f"已完成: {status['finished_count']}")
print(f"失败: {status['failed_count']}")

# 清除已完成任务
delegate.clear_finished()

# 重试所有失败任务
count = delegate.retry_all_failed()
print(f"重试了 {count} 个任务")
```

## 高级功能

### 自定义配置

```python
task = DownloadTask(
    url="https://www.bilibili.com/video/BV1xxx",
    output_dir="./downloads",
    config={
        "format": "bestaudio/best",  # 只下载音频
        "ratelimit": 1024 * 1024,    # 限速 1MB/s
        "proxy": "http://127.0.0.1:7890",
    }
)
```

### 优先级管理

```python
from util.download.task_manager import TaskPriority

# 高优先级任务（会先下载）
urgent_task = DownloadTask(
    url="https://www.bilibili.com/video/BV1xxx",
    output_dir="./downloads",
    priority=TaskPriority.URGENT
)

# 低优先级任务
low_task = DownloadTask(
    url="https://www.bilibili.com/video/BV2xxx",
    output_dir="./downloads",
    priority=TaskPriority.LOW
)
```

### 错误处理和重试

```python
def on_error(task, error_msg):
    if task.can_retry():
        print(f"任务失败，自动重试: {task.retry_count}/{task.max_retries}")
        delegate.retry_task(task.task_id)
    else:
        print(f"任务失败，已达最大重试次数: {error_msg}")

delegate.task_failed_signal.connect(on_error)
```

## 与现有项目集成

### 替换现有下载器

在现有的下载管理器中：

```python
# 在 src/util/download/downloader/manager.py 中
from util.download.yt_dlp_ui_delegate import YTDLPUIDelegate

class DownloadManager:
    def __init__(self):
        self.yt_dlp_delegate = YTDLPUIDelegate()
        self._connect_signals()
    
    def _connect_signals(self):
        self.yt_dlp_delegate.task_progress_signal.connect(self._on_progress)
        self.yt_dlp_delegate.task_finished_signal.connect(self._on_finished)
        self.yt_dlp_delegate.task_failed_signal.connect(self._on_error)
    
    def add_download_task(self, task_info):
        # 转换为 DownloadTask
        task = DownloadTask(
            url=task_info.url,
            output_dir=task_info.output_dir,
            title=task_info.title
        )
        return self.yt_dlp_delegate.add_task(task)
    
    def start_download(self, task_id):
        return self.yt_dlp_delegate.start_download()
```

### 混合使用

作为备用下载器：

```python
def download_with_fallback(self, task_info):
    # 先尝试现有下载器
    if self.existing_downloader.download(task_info):
        return True
    
    # 失败时使用 yt-dlp
    logger.warning("主下载器失败，切换到 yt-dlp")
    task = DownloadTask(
        url=task_info.url,
        output_dir=task_info.output_dir
    )
    task_id = self.yt_dlp_delegate.add_task(task)
    return self.yt_dlp_delegate.start_download()
```

## 测试

运行升级测试：

```bash
python test_yt_dlp_upgrade.py
```

## 注意事项

### 线程安全
- TaskManager 使用线程锁保护共享数据
- ControlledDownloader 在独立线程中运行
- 所有 UI 更新通过 Qt 信号机制

### yt-dlp 限制
- yt-dlp 本身不支持真正的 pause/resume
- 只能实现：cancel（取消）和 retry（重试）
- fragment resume 是间接支持的

### 性能考虑
- 默认单任务下载（max_concurrent=1）
- 可配置并发数量
- 自动重试机制

## 文件结构

```
src/util/download/
├── task_manager.py          # 任务管理器、状态机、受控下载器
├── yt_dlp_ui_delegate.py    # UI 代理（解耦层）
├── yt_dlp_downloader.py     # 原始下载器（保留）
├── yt_dlp_adapter.py        # 适配器（保留）
└── yt_dlp_integration.py    # 集成示例（保留）
```

## 总结

升级后的架构提供了：

- ✅ 正确的分层：UI → TaskManager → Downloader
- ✅ 完整的任务状态机
- ✅ 任务队列管理
- ✅ 受控下载器（start/stop/retry）
- ✅ UI 解耦层
- ✅ 线程安全实现
- ✅ 错误处理和重试机制
- ✅ 批量下载支持

这是一个生产级别的下载管理系统，可以直接用于你的项目。