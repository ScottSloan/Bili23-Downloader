
# Bili23 Downloader 技术文档

> **版本**: v2.00.7 | **许可证**: GPL-3.0 | **作者**: ScottSloan | **最终更新**: 2026-06-06

---

## 目录

1. [项目概述与建设目标](#1-项目概述与建设目标)
2. [完整技术栈说明](#2-完整技术栈说明)
3. [架构设计](#3-架构设计)
4. [核心模块详解](#4-核心模块详解)
5. [全流程业务流转说明](#5-全流程业务流转说明)
6. [部署运维指南](#6-部署运维指南)
7. [常见问题排查手册](#7-常见问题排查手册)
8. [附录](#8-附录)

---

## 1. 项目概述与建设目标

### 1.1 项目简介

Bili23 Downloader 是一款跨平台的 B 站（Bilibili）视频下载桌面工具，基于 Python 3.9+ 与 PySide6 构建。支持 **Windows（含 Win7）、Linux、macOS** 三大平台，提供现代化的 Fluent Design 风格图形用户界面。

### 1.2 核心能力

- **音视频流分离下载**：支持 DASH 格式视频流与音频流独立下载后本地合并
- **多线程分片下载**：每个文件按 4MB 分片并发下载，最大化带宽利用率，支持令牌桶限速
- **弹幕与字幕获取**：支持 XML/ASS 弹幕、SRT/LRC/ASS 字幕下载与格式转换
- **封面提取与元数据刮削**：自动获取视频封面、NFO/JSON 元数据
- **自定义文件命名**：支持基于约定规则（番剧/课程/分P/合集/普通视频）的自动文件命名与分类存储
- **账号登录**：支持二维码扫码登录与短信验证码登录，保持登录态
- **多种内容解析**：支持视频/BV号/剧集/课程/收藏夹/个人空间/稍后再看/历史记录/每周必看等链接

### 1.3 建设目标

| 目标 | 说明 |
|------|------|
| **跨平台一致性** | 基于 PySide6 + QFluentWidgets 实现 Windows/Linux/macOS 统一的 Fluent Design 体验 |
| **高下载性能** | 多线程分片下载 + 令牌桶限速，单任务最大支持 10 线程并发 |
| **内容完整性** | 不仅下载音视频，同时支持弹幕/字幕/封面/元数据的完整获取 |
| **用户友好** | 解析列表树形展示、搜索过滤、自动选择、自动解析分页、系统托盘通知 |
| **健壮性** | 断点续传、任务持久化（SQLite）、异常自动重试、单实例运行保护 |

---

## 2. 完整技术栈说明

### 2.1 运行时环境

| 类别 | 技术选型 | 版本 | 用途 |
|------|---------|------|------|
| **编程语言** | Python | ≥ 3.9 | 主体开发语言 |
| **GUI 框架** | PySide6 | 6.10.3 | Qt for Python 绑定，提供跨平台 UI 组件 |
| **UI 组件库** | PySide6-Fluent-Widgets | 1.11.2 | 微软 Fluent Design 风格的 Qt 组件库 |
| **HTTP 客户端** | httpx | 0.28.1 | 支持 HTTP/2、连接池、代理的现代 HTTP 客户端 |
| **数据序列化** | protobuf | 7.35.0 | 弹幕协议 Protobuf 反序列化 |
| **二维码生成** | qrcode | 8.2 | 登录二维码图片生成 |
| **系统监控** | psutil | 7.2.2 | 进程与系统资源监控 |
| **数据存储** | SQLite3 | 内建 | 下载任务持久化、封面图片缓存 |
| **音视频合并** | FFmpeg | 外部依赖 | 视频+音频流合并、容器格式转换、m4a→mp3 转码 |
| **构建打包** | PyInstaller / Nuitka | — | 最终分发打包 |

### 2.2 配置存储

- 使用 PySide6-Fluent-Widgets 内置的 `QConfig` 框架
- 配置文件路径：`{AppData}/Bili23 Downloader/config.json`
- 数据库路径：`{AppData}/Bili23 Downloader/task.db`
- 封面缓存数据库：`{AppData}/Bili23 Downloader/cover.db`

### 2.3 国际化（i18n）

| 语言 | 翻译文件 |
|------|---------|
| 简体中文 | `res/i18n/bili23.zh_CN.qm` / `.ts` |
| 繁体中文 | `res/i18n/bili23.zh_TW.qm` / `.ts` |
| 英文 | 代码内默认（英文原文写于代码中） |

---

## 3. 架构设计

### 3.1 分层架构图

```
┌──────────────────────────────────────────────────────────────────┐
│  GUI 表示层 (src/gui/)                                            │
│  ├── interface/         主界面路由（MainWindow/Parse/Download/    │
│  │                      Setting）                                 │
│  ├── component/         可复用视图组件（DownloadList/ParseList/    │
│  │                      EntryList/Widget/Setting/ViewModel）      │
│  └── dialog/            模态对话框（DownloadOptions/Login/Update/  │
│                          Setting子对话框/Misc杂项）                │
├──────────────────────────────────────────────────────────────────┤
│  信号总线 (src/util/common/signal_bus.py)                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐        │
│  │ Toast    │ Parse    │ Download │ Login    │ Update   │        │
│  │ 通知信号 │ 解析信号 │ 下载信号 │ 登录信号 │ 更新信号 │        │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘        │
├──────────────────────────────────────────────────────────────────┤
│  业务逻辑层 (src/util/)                                            │
│  ├── parse/           解析引擎（parser解析器 + episode剧集构建 +   │
│  │                    additional附加文件 + preview媒体预览）       │
│  ├── download/        下载引擎（downloader下载器 + task任务管理 +  │
│  │                    cover封面管理 + parse下载链接解析）          │
│  ├── auth/            认证模块（QRCode/SMS/Cookie/Captcha/User）  │
│  ├── ffmpeg/          FFmpeg调用封装（Command构建 + Runner执行）   │
│  ├── format/          格式化工具（文件名/时间/单位转换）            │
│  ├── misc/            杂项（更新检测/web/弹幕proto/解析历史）      │
│  └── thread/          线程管理（AsyncTask异步 + 线程池）           │
├──────────────────────────────────────────────────────────────────┤
│  基础设施层 (src/util/)                                            │
│  ├── network/         HTTP请求封装（httpx Client + Proxy + CDN）  │
│  ├── common/          通用基础设施（Config/SignalBus/Database/    │
│  │                    Enum/Icon/StyleSheet/Translator/Color/     │
│  │                    Serializer/Timestamp）                      │
│  └── res/             资源文件（图标/样式/翻译/HTML模板）           │
├──────────────────────────────────────────────────────────────────┤
│  外部依赖层                                                       │
│  ├── B站 API           api.bilibili.com 系列接口                   │
│  ├── FFmpeg            本地可执行文件                              │
│  ├── SQLite            本地数据库                                  │
│  └── VerHub            版本更新检测服务 (verhub.hanloth.cn)        │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 模块间依赖关系

```
main.py
  ├── gui/interface/main_window.py          # 主窗口（MSFluentWindow 子类）
  │   ├── gui/interface/parse.py            # 解析页（ParseInterface）
  │   │   ├── gui/component/parse_list/     # 解析列表树形视图
  │   │   ├── util/parse/worker.py          # 解析工作线程
  │   │   ├── util/parse/preview/           # 媒体预览
  │   │   └── util/download/task/manager.py # 下载任务创建
  │   ├── gui/interface/download.py         # 下载页（DownloadInterface）
  │   │   ├── gui/component/download_list/  # 下载列表视图
  │   │   └── util/download/task/           # 任务数据库查询
  │   └── gui/interface/setting.py          # 设置页（SettingInterface）
  │       └── gui/component/setting/        # 设置卡片组件
  │
  ├── util/common/signal_bus.py             # 全局事件总线（解耦模块通信）
  ├── util/common/config.py                 # 全局配置管理（QConfig）
  ├── util/common/database.py               # SQLite 数据库基类
  │
  ├── util/auth/                            # 登录认证
  │   ├── base.py       → util/network/request.py
  │   ├── qrcode.py     → qrcode 库
  │   ├── sms.py        → util/auth/captcha.py
  │   └── cookie.py     → util/network/request.py
  │
  ├── util/network/                         # 网络层
  │   ├── request.py    → httpx.Client
  │   ├── proxy.py      → util/common/config.py
  │   └── cdn.py        → util/common/config.py
  │
  └── util/ffmpeg/                          # FFmpeg 封装
      ├── command.py    # 命令构建器
      └── runner.py     # QThread 子进程执行器
```

### 3.3 数据流向总览

```
用户输入 URL/关键字
    │
    ▼
ParseInterface.on_parse()
    │
    ▼
ParseWorker.run()                        ← 后台线程
    ├── 匹配 URL 模式 → 选择 Parser
    ├── 调用 B 站 API 获取原始数据
    ├── EpisodeParser 构建树形数据结构
    └── Signal → 更新 ParseTreeView
    │
    ▼
用户勾选下载项 → 点击下载
    │
    ▼
TaskManager.create(task_list)             ← signal_bus.download.create_task
    ├── 生成 UUID task_id
    ├── 读取配置（画质/音质/编码/附加文件）
    ├── 写入 SQLite (download_task 表)
    └── Signal → 加入前端下载列表
    │
    ▼
DownloaderManager.add(task_info)
    ├── Downloader.start()
    │   ├── ParseWorker → 请求播放链接 (api.bilibili.com/x/player/wbi/playurl)
    │   ├── TokenBucket 令牌桶限速
    │   ├── ChunkWorker × N  → httpx.stream() 分片下载
    │   ├── 速度采样 QTimer (每秒)
    │   └── 下载完成 → AdditionalParseWorker (弹幕/字幕/封面/元数据)
    │       └── 加入 FFmpeg 合并队列
    │           ├── FFmpegRunner → 调用外部 ffmpeg 进程
    │           └── 文件重命名/清理
    │               └── 迁移到 completed_task 表
    └── Signal → 更新下载列表 UI
```

---

## 4. 核心模块详解

### 4.1 入口模块 (`src/main.py`)

**职责**：应用初始化、日志配置、Qt 警告过滤、单实例锁、窗口创建与启动。

**关键流程**：

1. 配置日志系统（控制台输出 + 按日滚动的文件日志，路径 `{AppData}/Bili23 Downloader/logs/app.log`）
2. 安装 Qt 消息处理器，过滤 `QFont::setPointSize` / `OpenType support missing` 等噪音警告
3. 初始化 `Application`（`QApplication` 子类）：
   - 单实例锁：通过 `QLockFile` + `QLocalServer`/`QLocalSocket` 实现
   - Windows 额外互斥体（`CreateMutexW`）防止多开
   - 二次激活：已有实例运行时，传递消息激活已存在的窗口
4. 加载多语言翻译（FluentTranslator + 自定义 bili23 Qt 翻译文件）
5. 创建 `MainWindow` 窗口，延迟初始化非关键服务（Cookie/用户信息）
6. 启动事件循环 `app.exec()`

**配置项**：
- `display_scaling`：控制缩放比例（100%/125%/150%/175%/200%/Auto），影响 `QT_SCALE_FACTOR` 环境变量
- `language`：语言选择（zh_CN/zh_TW/en/Auto）
- `tutorial_dialog_shown`：首次使用引导弹窗

### 4.2 信号总线 (`src/util/common/signal_bus.py`)

**职责**：全局事件总线，解耦 GUI 各组件与业务逻辑层之间的通信。采用单例模式。

**信号分组**：

| 分组 | 关键信号 | 说明 |
|------|---------|------|
| `ToastNotification` | `show`, `show_long_message`, `sys_show` | 三类 Toast 通知（短暂/长时间/系统通知） |
| `Parse` | `update_parse_list`, `parse_url`, `preview_init/finish`, `query_video/audio_info`, `update_column_settings`, `search_keyword`, `show_interactive_video_dialog` | 解析流程相关信号 |
| `Download` | `create_task`, `add_to_downloading/completed_list`, `update_downloading_item/count`, `start_next_task`, `auto_manage_concurrent_downloads`, `remove_from_*`, `sort_*` | 下载流程全生命周期信号 |
| `Login` | `start_server/stop_server`, `send_sms`, `update_avatar` | 登录相关信号 |
| `Update` | `check`, `show_dialog` | 版本更新信号 |
| `Interface` | `mica_effect_changed` | 界面效果信号 |

**延迟发射机制**：

主窗口初始化完成前（`config.main_window_ready == False`），信号会暂存在 `pending_signals` 列表中，并使用线程锁 `Lock` 保证多线程安全。初始化完成后通过 `emit_pending_signals()` 批量发送。

### 4.3 配置管理 (`src/util/common/config.py`)

**`APPConfig` 类**继承自 `QConfig`，包含以下配置分组：

| 分组 | 关键配置项 | 类型 | 默认值 |
|------|-----------|------|--------|
| **Interface** | `language`, `display_scaling`, `mica_effect` | Options/Options/Bool | Auto/Auto/False |
| **Behavior** | `monitor_clipboard`, `show_download_confirmation_dialog`, `auto_select_mode`, `when_close_window`, `file_conflict_resolution`, `preallocate_file_space`, `parse_history` | 混合 | 见源码 |
| **Download** | `download_path`, `download_thread`(1-10), `download_parallel`(1-10), `speed_limit_enabled/rate`, `video_quality_priority`, `audio_quality_priority`, `video_codec_priority`, `video_container`, `m4a_to_mp3` | 混合 | 见源码 |
| **Additional** | `download_danmaku/subtitle/cover/metadata`, `danmaku/subtitle_type/style`, `cover_type`, `metadata_type` | 混合 | 见源码 |
| **File Naming** | `naming_rule_list`, `numbering_type`, `starting_number` | Config/Options/Config | 见源码 |
| **Advanced** | `prefer_cdn_server_provider`, `cdn_server_list`, `ffmpeg_source/path`, `proxy_enabled/type/server/port/uname/password`, `user_agent` | 混合 | 见源码 |
| **Update** | `include_prerelease` | Bool | False |
| **Cookie** | `img_key`, `sub_key`, `bili_jct`, `DedeUserID`, `SESSDATA`, `uuid`, `b_lsid`, `b_nut`, `bili_ticket`, `buvid3/4` | Config | 空 |

**运行时变量**（不持久化，存于 `config` 对象属性）：

- `video_quality_id` / `audio_quality_id` / `video_codec_id`：实时解析得到的画质/音质/编码 ID
- `download_video_stream` / `download_audio_stream` / `merge_video_audio` / `keep_original_files`：下载选项
- `current_starting_number` / `global_starting_number`：文件编号状态
- `no_ffmpeg_available`：FFmpeg 可用性标记
- `is_expired`：登录态过期标记（Cookie 中的 `is_expired` 派生）

### 4.4 网络请求层 (`src/util/network/`)

**`request.py`**：

| 类/函数 | 职责 |
|---------|------|
| `_ensure_client()` | 懒加载创建 `httpx.Client` 单例，配置连接池(10)、超时(5s)、代理 |
| `_LazyClientProxy` | 代理类，`client.get/post/...` 自动路由到 `_ensure_client()` 返回的实例 |
| `SyncNetWorkRequest` | 同步网络请求封装，支持 GET/POST/HEAD，返回 TEXT/JSON/BYTES/HEADERS/REDIRECT_URL/RESPONSE |
| `get_cookies()` | 从 `config` 中读取 Cookie 字典 |
| `update_cookies()` | 将当前 `client.cookies` 同步回 `config` |

**CDN 服务器列表**（6 个默认节点）：

| Host | 提供商 |
|------|--------|
| `upos-sz-mirror08c.bilivideo.com` | 华为 |
| `upos-sz-mirrorhw.bilivideo.com` | 华为 |
| `upos-sz-mirrorcos.bilivideo.com` | 腾讯 |
| `upos-sz-mirrorcosb.bilivideo.com` | 腾讯 |
| `upos-sz-mirrorali.bilivideo.com` | 阿里云 |
| `upos-sz-mirroralib.bilivideo.com` | 阿里云 |

### 4.5 解析引擎 (`src/util/parse/`)

#### 4.5.1 架构层次

```
src/util/parse/
├── worker.py                 # ParseWorker / ProgressParseWorker（入口调度）
├── parser/                   # 一级解析器：从 URL 获取原始 API 数据
│   ├── base.py               # ParserBase（WBI 签名、响应检查、登录校验）
│   ├── video.py              # VideoParser（普通视频 + InteractiveVideoParser 互动视频）
│   ├── bangumi.py            # BangumiParser（番剧/影视 ep/ss/md）
│   ├── cheese.py             # CheeseParser（课程）
│   ├── space.py              # SpaceParser（个人空间）
│   ├── favlist.py            # FavlistParser（收藏夹）
│   ├── list.py               # ListParser（合集列表）
│   ├── popular.py            # PopularParser（每周必看）
│   ├── watch_later.py        # WatchLaterParser（稍后再看）
│   ├── history.py            # HistoryParser（历史记录）
│   ├── dynamic.py            # DynamicParser（动态视频）
│   ├── favorite.py           # FavoriteParser（收藏夹列表）
│   └── b23.py                # B23Parser（b23.tv 短链解析）
├── episode/                  # 二级解析器：将 API 原始数据构建为树形剧集结构
│   ├── base.py               # EpisodeParserBase
│   ├── tree.py               # TreeItem / TreeItemBase / Attribute / EpisodeData
│   ├── video.py              # VideoEpisodeParser（单视频 / 分P / 合集）
│   ├── bangumi.py            # BangumiEpisodeParser（番剧分季）
│   ├── cheese.py             # CheeseEpisodeParser（课程集数）
│   └── ...                   # 其他对应 parser
├── additional/               # 附加文件解析器
│   ├── worker.py             # AdditionalParseWorker（调度器）
│   ├── danmaku.py            # 弹幕下载（调用 file/danmaku_ass.py, file/danmaku_xml.py）
│   ├── subtitles.py          # 字幕下载（调用 file/subtitle_ass.py）
│   ├── cover.py              # 封面下载
│   ├── metadata.py           # 元数据刮削（调用 file/metadata_nfo.py）
│   └── file/                 # 文件生成器
│       ├── danmaku_ass.py    # ASS 格式弹幕
│       ├── danmaku_xml.py    # XML 格式弹幕（含 Protobuf 反序列化 dm_pb2.py）
│       ├── subtitle_ass.py   # ASS 格式字幕
│       └── metadata_nfo.py   # NFO 格式元数据（Kodi 标准）
└── preview/                  # 媒体预览模块
    ├── previewer.py          # Previewer（协调视频/音频信息获取）
    ├── info.py               # PreviewerInfo（全局预览状态）
    ├── video_info.py         # 视频质量/编码解析
    ├── audio_info.py         # 音频质量解析
    └── worker.py             # 工作线程
```

#### 4.5.2 WBI 签名算法

`ParserBase.enc_wbi(params)` 实现了 B 站 WBI 签名：

1. 从 `config` 获取 `img_key` + `sub_key`
2. 通过固定置换表 `mixinKeyEncTab` 计算出 32 位 `mixin_key`
3. 添加 `wts`（当前时间戳），按 key 排序
4. 过滤特殊字符 `!'()*`
5. 计算 `md5(query_string + mixin_key)` 作为 `w_rid`

#### 4.5.3 树形数据结构 (`TreeItem` / `Attribute`)

每个解析结果构建为一棵 `TreeItem` 树：

```
Root (不可见)
├── 分类节点 (TREE_NODE_BIT)
│   ├── 章节节点 (TREE_NODE_BIT)      ← 合集结构
│   │   ├── 分P节点 (TREE_NODE_BIT)   ← 合集内多P视频
│   │   │   ├── Video Item (VIDEO_BIT | PART_BIT)
│   │   │   └── Video Item
│   │   └── Video Item (VIDEO_BIT | COLLECTION_BIT)
│   ├── Video Item (VIDEO_BIT | PART_BIT)   ← 分P结构
│   └── Video Item (VIDEO_BIT | NORMAL_BIT)  ← 单视频结构
└── Bangumi Item (BANGUMI_BIT)
```

**`Attribute` 标志位（IntFlag）**用于标识节点的属性：

| 标志位 | 值 | 含义 |
|--------|-----|------|
| `VIDEO_BIT` | 1<<0 | 投稿视频 |
| `BANGUMI_BIT` | 1<<1 | 番剧/影视 |
| `CHEESE_BIT` | 1<<2 | 课程 |
| `POPULAR_BIT` | 1<<3 | 每周必看 |
| `COLLECTION_LIST_BIT` | 1<<4 | 合集列表 |
| `SPACE_BIT` | 1<<5 | 个人空间 |
| `FAVLIST_BIT` | 1<<6 | 收藏夹 |
| `NEED_PARSE_BIT` | 1<<7 | 需二次解析（空间/收藏夹中的视频） |
| `NORMAL_BIT` | 1<<8 | 单个视频 |
| `PART_BIT` | 1<<9 | 分P视频 |
| `TREE_NODE_BIT` | 1<<15 | 树节点（非叶子） |

**`EpisodeData`**：全局剧集数据字典 `table: dict[str, dict]`，用于 parser 与 episode 之间的数据传递（通过 UUID `episode_id` 索引）。

### 4.6 下载引擎 (`src/util/download/`)

#### 4.6.1 模块架构

```
src/util/download/
├── downloader/                    # 下载器子系统
│   ├── downloader.py              # Downloader（主下载器类，QObject）
│   │   ├── TokenBucket            # 令牌桶速率控制
│   │   ├── ChunkWorker            # 分片下载工作单元（QRunnable）
│   │   └── Downloader             # 下载生命周期管理
│   ├── manager.py                 # DownloaderManager（全局下载器管理器）
│   ├── parse_worker.py            # 下载链接解析器（QRunnable + ParserBase）
│   └── merger.py                  # Merger（FFmpeg 合并调度器）
│
├── task/                          # 任务管理子系统
│   ├── info.py                    # TaskInfo 数据类（BasicInfo/FileInfo/EpisodeInfo/DownloadInfo）
│   ├── manager.py                 # TaskManager（任务创建/数据库持久化/文件命名）
│   ├── db.py                      # TaskDatabase（SQLite CRUD）
│   ├── query_worker.py            # QueryWorker（启动时从 DB 恢复任务）
│   └── reparse_worker.py          # ReparseWorker（重新解析链接）
│
├── cover/                         # 封面管理子系统
│   ├── manager.py                 # CoverManager（封面查询/缓存/请求调度）
│   ├── db.py                      # CoverDatabase（SQLite blob 存储）
│   ├── cache.py                   # CoverCache（内存缓存字典）
│   └── query_worker.py            # CoverQueryWorker（异步封面加载）
│
└── parse/                         # 下载链接解析
    ├── video_info.py              # 视频流信息解析
    ├── audio_info.py              # 音频流信息解析
    └── query_worker.py            # 异步查询工作线程
```

#### 4.6.2 TaskInfo 数据类

```python
@dataclass
class TaskInfo:
    Basic: BasicInfo       # task_id, cover_id, show_title, created_time, completed_time
    File: FileInfo         # name, download_path, folder, video/audio/merge_file_ext, relative_files
    Episode: EpisodeInfo   # aid, bvid, cid, cover, title, duration, 各类媒体属性...
    Download: DownloadInfo # type(位标志), media_type, speed, progress, total_size, status, queue, files...
```

**`DownloadInfo.type`** 使用位标志组合：

```python
class DownloadType(IntEnum):
    VIDEO = 1
    AUDIO = 2
    DANMAKU = 4
    SUBTITLE = 8
    COVER = 16
    METADATA = 32
```

#### 4.6.3 下载状态机

```
QUEUED → PARSING → DOWNLOADING → ADDITIONAL_PROCESSING → FFMPEG_QUEUED → MERGING → COMPLETED
                     ↓                ↓                        ↓              ↓
                   FAILED          PAUSED                   FAILED      FFMPEG_FAILED
                     ↓                ↓
                  可重试          可恢复
```

**状态说明**：

| 状态 | 含义 |
|------|------|
| `QUEUED` | 已加入队列，等待开始 |
| `PARSING` | 正在解析下载链接 |
| `DOWNLOADING` | 正在下载媒体文件 |
| `PAUSED` | 用户暂停 |
| `ADDITIONAL_PROCESSING` | 正在下载弹幕/字幕/封面/元数据 |
| `FFMPEG_QUEUED` | 等待 FFmpeg 合并 |
| `MERGING` | 正在 FFmpeg 合并 |
| `COMPLETED` | 下载完成 |
| `FAILED` | 下载失败（可重试） |
| `FFMPEG_FAILED` | FFmpeg 合并失败（可重试） |

#### 4.6.4 TokenBucket 令牌桶算法

```python
class TokenBucket:
    def __init__(self, rate: float):   # rate: 字节/秒，0 = 不限速
    def consume(self, amount: int, stop_event: Event = None):
        # 计算需要等待的时间，分段休眠（0.1s 粒度），可被 stop_event 中断
    def set_rate(self, rate: float):   # 动态调整速率
```

#### 4.6.5 ChunkWorker 分片策略

- 每个文件按 **4MB** 固定大小分片
- 每个分片运行在独立的 `QRunnable` 中
- 支持 5 次自动重试，指数退避（`min(2^(attempt-1), 8)` 秒）
- 可重试错误码：`{408, 429, 500, 502, 503, 504}` + 系统 I/O 错误
- 不可重试错误码：`{400, 401, 403, 404, 405, 410, 416}` + 权限/磁盘满错误
- 下载进度实时上报（通过 `QMetaObject.invokeMethod` 线程安全更新 UI）

### 4.7 认证模块 (`src/util/auth/`)

| 模块 | 职责 |
|------|------|
| `cookie.py` | CookieManager：初始化 buvid3/buvid4/bili_ticket/指纹（MurmurHash3）等非登录态 Cookie |
| `qrcode.py` | QRCode：生成登录二维码 → 轮询扫码状态（每 2 秒） → 获取登录 Cookie |
| `sms.py` | SMS：发送短信验证码 → 收集 cid/手机号/验证码/极验 Captcha → 提交登录 |
| `captcha.py` | Captcha：加载极验验证码 WebView（`res/html/captcha.html`） → 获取 validate/seccode |
| `user.py` | UserManager：获取用户信息（昵称/UID/头像） → signal_bus.login.update_avatar |
| `server.py` | AuthServer：本地 HTTP 服务器，用于接收第三方登录回调（如 OAuth） |

### 4.8 FFmpeg 模块 (`src/util/ffmpeg/`)

**`FFmpegCommand`**：建造者模式构建 FFmpeg 命令行参数

| 静态方法 | 用途 |
|---------|------|
| `merge_video_audio()` | 合并 DASH 视频流 + 音频流，可选附加封面 |
| `merge_video_parts()` | 合并 FLV 分片（concat demuxer） |
| `convert_m4a_to_mp3()` | m4a 音频转 mp3 |

**`FFmpegRunner(QThread)`**：在独立线程中调用 `subprocess.Popen` 执行 FFmpeg 命令。

- Windows 使用 `CREATE_NO_WINDOW` 避免弹出命令行窗口
- `errors="replace"` 处理编码不兼容字符
- 自动捕获 stdout/stderr 并返回
- 支持 `terminate()` 强制终止

**FFmpeg 来源策略**（`FFmpegSource` 枚举）：

| 来源 | 说明 |
|------|------|
| `BUNDLED` | 打包在应用内的 FFmpeg（默认） |
| `SYSTEM` | 系统 PATH 中的 FFmpeg |
| `CUSTOM` | 用户自定义路径 |

### 4.9 GUI 组件体系

#### 4.9.1 主窗口路由 (`MainWindow`)

基于 `MSFluentWindow`，左侧导航栏包含：

```
[搜索图标] → ParseInterface     (routeKey: "ParseInterface")
[下载图标] → DownloadInterface  (routeKey: "DownloadInterface")
[收藏图标] → Flyout 弹出面板    (显示收藏夹列表)
[关于图标] → AboutDialog
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[头像按钮] → LoginDialog / ProfileCard
[设置图标] → SettingInterface   (routeKey: "SettingInterface")
```

系统托盘图标（`SystemTrayIcon`）支持最小化到托盘、关闭窗口行为配置。

#### 4.9.2 解析页 (`ParseInterface`)

**UI 组件**：

```
┌──────────────────────────────────────────────┐
│ [URL 输入框                        ] [解析]   │
├──────────────────────────────────────────────┤
│ 投稿视频 (共 N 个)         [选项] [更多]      │
├──────────────────────────────────────────────┤
│ ☑ 视频标题1             00:12:34  2024-01-01 │
│ ☐ 视频标题2             00:05:21  2024-01-02 │
│ ...                                         │
├──────────────────────────────────────────────┤
│ [搜索框] [◀ 1/3 ▶] [▸]  [季选择▼]  [进度]   │
│                              [下载选中项目]   │
└──────────────────────────────────────────────┘
```

**核心功能**：

| 功能 | 触发方式 | 说明 |
|------|---------|------|
| URL 解析 | 输入框回车 / 粘贴解析 / 点击解析按钮 | 异步调用 ParseWorker |
| 分页浏览 | 翻页按钮 | 带分页的资源（空间/收藏夹）自动显示分页组件 |
| 季切换 | SeasonComboBox | 番剧多季切换 |
| 搜索过滤 | 搜索框 | 实时过滤解析列表中的项目 |
| 自动选择 | 根据 auto_select_mode 配置 | MANUAL/CONDITIONAL/SELECT_ALL |
| 自动解析分页 | AutoParseDialog | 自动遍历所有分页并解析 |
| 互动视频 | InteractiveVideoDialog | BFS 遍历互动视频剧情图 |
| 剪贴板监听 | QClipboard.changed | 可选，自动检测剪贴板中的 B 站链接 |
| 下载确认对话框 | DownloadOptionsDialog | 可选，下载前确认选项 |

#### 4.9.3 下载页 (`DownloadInterface`)

**双标签页**：正在下载 / 已完成

**下载列表项功能**：

| 状态 | 右键菜单选项 |
|------|------------|
| `COMPLETED` | 重新解析、重新下载、删除 |
| `QUEUED` / `PAUSED` | 恢复、重新下载、删除 |
| `DOWNLOADING` | 暂停、重新下载、删除 |

**批量操作**：全部开始 / 全部暂停 / 全部删除（下载中）/ 清空（已完成）

**底部状态栏**：显示正在下载数量（红点角标）

### 4.10 异步任务机制

**`AsyncTask.run(worker)`**（`src/util/thread/async_.py`）：

1. 创建 `QThread`
2. 将 `worker`（`QObject` 子类）移动到新线程
3. 连接 `thread.started → worker.run`
4. 连接 `worker.finished → thread.quit → worker.deleteLater`
5. 加入全局线程队列 `thread_queue`
6. `AsyncTask.safe_quit()` 在应用关闭时依次退出所有线程

**GlobalThreadPoolTask**（`src/util/thread/pool.py`）：

- 封装 `QThreadPool.globalInstance()` 用于 `QRunnable` 任务
- `run_func()` 将普通函数包装为 `QRunnable`

---

## 5. 全流程业务流转说明

### 5.1 URL 解析流程

```
触发：用户在 ParseInterface 输入 URL 并点击解析
        │
        ▼
ParseWorker.__init__(url, pn)
        │
        ▼
ParseWorker.run()                              ← QThread 执行
        │
        ├── EpisodeData.clear_cache()          ← 清空全局剧集数据
        ├── get_parser_type(url)               ← 正则匹配 URL 模式
        │   └── 匹配 url_patterns 字典 (src/util/common/data/url_pattern.py)
        │       ├── "BV..." / "av..."             → video
        │       ├── "ep..." / "ss..." / "md..."   → bangumi
        │       ├── "cheese..."                   → cheese
        │       ├── "space.bilibili.com/..."      → space
        │       ├── "favorite..."                 → favlist
        │       ├── "collection..."               → list
        │       ├── "popular..."                  → popular
        │       ├── "watchlater"                  → watch_later
        │       └── "history"                     → history
        │
        ├── get_redirect_url()
        │   ├── 匹配 b23.tv → B23Parser 解析短链重定向
        │   └── 匹配 festival → FestivalParser 处理活动页
        │
        ├── Parser.parse(url, pn)               ← 调用对应解析器
        │   │
        │   ├── [VideoParser]
        │   │   ├── aid_to_bvid()  或  get_bvid()
        │   │   ├── enc_wbi(params) → 签名
        │   │   ├── GET api.bilibili.com/x/web-interface/wbi/view
        │   │   │
        │   │   ├── 判断 is_interactive_video?
        │   │   │   ├── YES → emit show_interactive_video_dialog
        │   │   │   │           → InteractiveVideoParser BFS 遍历剧情图
        │   │   │   │           → DynamicEpisodeParser 构建节点
        │   │   │   └── NO  → VideoEpisodeParser.parse()
        │   │   │              ├── ugc_season? → 合集结构
        │   │   │              ├── pages > 1?  → 分P结构
        │   │   │              └── else        → 单视频结构
        │   │   │
        │   │   └── check_redirect_url() → 重定向 URL 自动重新解析
        │   │
        │   └── [BangumiParser]
        │       ├── 识别 ep/ss/md
        │       ├── GET api.bilibili.com/pgc/view/web/season
        │       └── BangumiEpisodeParser.parse()
        │           ├── 单 ep → 定位到具体剧集
        │           └── ss/md → 展示全季 + seasons 列表
        │
        ├── 获取 category_name + extra_data
        │       │
        │       ▼
        ├── emit success(category_name, extra_data)
        │   │
        │   └── ParseInterface.on_parse_success()
        │       ├── parse_list.update_tree() → TreeView 刷新
        │       ├── check_extra_data()       → 分页/季选择组件
        │       ├── apply_auto_select()      → 自动勾选
        │       └── Previewer.on_init()      → 媒体信息预览
        │           ├── get_video/bangumi/cheese_info()
        │           ├── check DRM?
        │           ├── parse_quality_info() / parse_codec_info()
        │           └── emit preview_finish()
        │
        └── emit finished() → 清理 parser 缓存
```

### 5.2 下载任务创建流程

```
触发：用户勾选视频并点击"下载选中项目"
        │
        ▼
ParseInterface.on_download()
        │
        ├── [if show_download_confirmation_dialog]
        │   └── DownloadOptionsDialog 确认选项
        │       ├── 画质选择（基于视频质量优先级列表过滤）
        │       ├── 音质选择（基于音频质量优先级列表过滤）
        │       ├── 编码选择（AV1/HEVC/AVC）
        │       ├── 附加选项（弹幕/字幕/封面/元数据开关）
        │       └── 保存设置到 config 运行时变量
        │
        ├── parse_list.get_checked_items(to_dict=True, mark_as_downloaded=True)
        │   └── 遍历选中的 TreeItem，提取 episode_info
        │
        ├── signal_bus.download.create_task.emit(task_list)
        │   │
        │   └── TaskManager.create(task_list)
        │       ├── 遍历每个 episode_info
        │       │   ├── __episode_info_to_task_info()
        │       │   │   ├── 生成 UUID task_id
        │       │   │   ├── 读取 config 确定 DownloadType 位标志
        │       │   │   ├── __update_episode_info()
        │       │   │   │   ├── 从 EpisodeData 获取补充数据
        │       │   │   │   ├── 过滤文件名非法字符
        │       │   │   │   └── 确定 numbering（文件编号）
        │       │   │   └── __update_file_name_info()
        │       │   │       ├── 读取 naming_rule_list 获取命名规则
        │       │   │       ├── FileNameFormatter 按约定类型格式化
        │       │   │       └── 生成 download_path/folder/file_name
        │       │   │
        │       │   └── TaskDatabase.add_tasks([task_info])
        │       │
        │       └── emit add_to_downloading_list(task_info_list)
        │           └── DownloadInterface.downloading_list_view.addTask()
        │               └── DownloadListModel.appendRow() → UI 更新
        │
        └── signal_bus.download.auto_manage_concurrent_downloads.emit()
            └── DownloadListView._schedule_auto_manage_concurrent_downloads()
                └── 根据 download_parallel 配置启动任务
```

### 5.3 视频下载完整流程

```
Downloader.start()                              ← DownloaderManager 调用
        │
        ├── 检查进度 ≥ 100%? → on_download_completed()
        │
        ├── 创建 ParseWorker (QRunnable)
        │   │
        │   └── ParseWorker.run()
        │       ├── 根据 attribute 判断 API
        │       │   ├── VIDEO_BIT  → api.bilibili.com/x/player/wbi/playurl
        │       │   ├── BANGUMI_BIT → api.bilibili.com/pgc/player/web/playurl
        │       │   └── CHEESE_BIT → api.bilibili.com/pugv/player/web/playurl
        │       │
        │       ├── 判断媒体类型: DASH / MP4 / FLV
        │       ├── parse_download_info()
        │       │   ├── VideoInfoParser (视频流 URL + 大小)
        │       │   ├── AudioInfoParser (音频流 URL + 大小)
        │       │   └── 组装 download_list + download_queue
        │       │
        │       └── emit on_parse_finished(download_info_json)
        │
        ├── Downloader.on_parse_finished()
        │   ├── 记录 download_list / download_queue
        │   ├── update_task_info (画质标签等)
        │   ├── start_worker()                    ← 启动分片下载
        │   └── start_timer()                     ← 启动速度采样 (每秒)
        │
        ├── start_worker()
        │   ├── 取 download_queue[0] (文件标识: video/audio)
        │   ├── 创建目标文件目录
        │   ├── _check_disk_space() → 必要时预分配文件
        │   ├── calc_chunk_list()   → 计算分片列表
        │   ├── 并行启动 ChunkWorker × N
        │   │   │
        │   │   └── 每个 ChunkWorker.run()
        │   │       ├── httpx.stream("GET", url, Range: bytes=X-Y)
        │   │       ├── 写入目标文件对应偏移位置
        │   │       ├── TokenBucket.consume() 限速
        │   │       ├── 更新 downloaded_size (加 thread lock)
        │   │       ├── 异常 → 退避重试 (最多 5 次)
        │   │       └── 完成 → invokeMethod on_chunk_finished()
        │   │
        │   └── task_manager.update() → 持久化进度到 SQLite
        │
        ├── on_chunk_finished(file_key, chunk_index)
        │   ├── 从 chunks_list 移除已完成分片
        │   ├── 检查文件是否全部完成
        │   │   ├── 完成 → 从 queue 移除该文件
        │   │   │   └── queue 仍有文件 → start_worker() 继续下一文件
        │   │   │   └── queue 为空 → on_download_completed()
        │   │   └── 未完成 → 继续等待
        │   └── task_manager.update() → 持久化进度
        │
        ├── on_download_completed()
        │   ├── 检查 DownloadType 位标志
        │   │   ├── 有附加文件 (弹幕/字幕/封面/元数据)
        │   │   │   └── AdditionalParseWorker.run()
        │   │   │       ├── DanmakuParser.parse()    → XML/ASS 弹幕文件
        │   │   │       ├── SubtitlesParser.parse()  → SRT/ASS 字幕文件
        │   │   │       ├── CoverParser.parse()      → JPG/PNG 封面
        │   │   │       └── MetadataParser.parse()   → NFO/JSON 元数据
        │   │   │           │
        │   │   │           └── 完成 → success Signal → wait_merge()
        │   │   │
        │   │   └── 无附加文件 → wait_merge()
        │   │
        │   └── wait_merge()
        │       ├── 等待所有 ChunkWorker 线程完成 (active_workers → 0)
        │       ├── 状态 → FFMPEG_QUEUED
        │       ├── signal_bus.download.auto_manage_concurrent_downloads.emit()
        │       └── DownloaderManager 调度 → Merger.start()
        │
        └── Merger.start()
            ├── merge_video_audio?
            │   └── FFmpegCommand.merge_video_audio() → FFmpegRunner
            │       ├── ffmpeg -i video.m4s -i audio.m4s [-i cover.jpg]
            │       │          -map 0:v:0 -map 1:a:0 [-map 2:v:0]
            │       │          -c:v copy -c:a copy [-c:v:1 mjpeg
            │       │          -disposition:v:1 attached_pic]
            │       │          output.mp4
            │       ├── 成功 → 删除临时文件
            │       ├── 失败 → FFMPEG_FAILED 状态
            │       └── rename_output_file() → 最终文件名
            │
            ├── merge_video_parts?
            │   └── FFmpegCommand.merge_video_parts() → FFmpegRunner
            │       └── ffmpeg -f concat -i list.txt -c copy output.mp4
            │
            ├── m4a_to_mp3?
            │   └── FFmpegCommand.convert_m4a_to_mp3() → FFmpegRunner
            │
            └── 完成 →
                ├── 状态 → COMPLETED
                ├── TaskDatabase: download_task → 删除, completed_task → 插入
                ├── emit add_to_completed_list()
                └── DownloaderManager.show_notification() → 系统托盘通知
```

### 5.4 登录认证流程

#### 5.4.1 二维码登录

```
LoginDialog 打开
    │
    ├── QRCode.generate()
    │   ├── GET passport.bilibili.com/x/passport-login/web/qrcode/generate
    │   ├── 构建 QPixmap 二维码图片 (qrcode 库 → QImage → QPainter)
    │   └── emit qrcode_generated(pixmap)
    │
    ├── QTimer (每 2 秒轮询)
    │   │
    │   └── QRCode.check_scan_status()
    │       ├── GET passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=xxx
    │       ├── code == 86101 → WAITING_FOR_SCAN (等待扫码)
    │       ├── code == 86090 → WAITING_FOR_CONFIRMATION (等待确认)
    │       ├── code == 0     → SUCCESS
    │       │   ├── 提取 Cookie (DedeUserID/SESSDATA/bili_jct/...)
    │       │   ├── update_cookies() → client.cookies + config
    │       │   └── dialog.accept()
    │       └── code == 86038 → EXPIRED (重新生成)
    │
    └── 登录成功 → CookieManager 刷新 Token → UserManager 获取用户信息
```

#### 5.4.2 短信验证码登录

```
用户输入手机号 → 点击获取验证码
    │
    ├── SMS.send_captcha_code()
    │   ├── Captcha 获取极验验证码
    │   │   ├── 加载 captcha.html WebView
    │   │   ├── 用户完成人机验证
    │   │   └── 获取 geetest_challenge/validate/seccode
    │   │
    │   └── POST passport.bilibili.com/x/passport-login/sms/send
    │       ├── 参数: cid, tel, captcha_key, geetest_*
    │       └── 成功 → 发送验证码
    │
    └── 用户输入验证码 → 点击登录
        │
        └── SMS.login()
            ├── POST passport.bilibili.com/x/passport-login/sms/login
            │   └── 参数: cid, tel, code, captcha_key
            └── 成功 → 提取 Cookie → 登录完成
```

### 5.5 自动解析流程

```
用户点击自动解析分页按钮
    │
    ├── AutoParseDialog → 用户确认选项
    │   ├── auto_select_mode: current / all / main
    │   └── payload → AutoParsePayload
    │
    ├── ProgressParseWorker.run()
    │   ├── 根据 parser_type 选择
    │   │   ├── INTERACTIVE_VIDEO → InteractiveVideoParser
    │   │   │   └── BFS 遍历剧情图，逐个节点调用 API
    │   │   └── DYNAMIC → DynamicParser
    │   │
    │   └── 进度回传 → update_progress Signal
    │       └── ParseInterface.progress_widget 显示进度
    │
    └── 完成 → emit success() → parse_list 更新
```

### 5.6 更新检测流程

```
应用启动后 → signal_bus.update.check.emit(manual=False)
    │
    └── Updater.request_update(manual=False)
        │
        ├── POST verhub.hanloth.cn/api/v1/public/scottsloan-bili23-downloader/versions/check-update
        │   └── 参数: current_version, current_comparable_version, include_preview
        │
        └── Updater.check(response)
            ├── should_update == False → 无操作（manual 时 toast 提示已是最新）
            ├── skip_version == version → 跳过
            └── should_update == True → emit show_update_dialog(info)
                └── MainWindow.show_update_dialog() → UpdateDialog
                    └── 显示更新内容 + 下载链接
```

### 5.7 异常分支处理总结

| 场景 | 处理方式 |
|------|---------|
| **URL 无效** | `get_parser_type()` 抛出 `ValueError("无效的链接")` → Toast 错误提示 |
| **API 返回 code != 0** | `ParserBase.check_response()` 抛出异常 → Toast 显示 API 错误消息 |
| **需要登录但未登录** | `check_login()` 抛出 `Exception` → Toast 引导登录 |
| **DRM 保护内容** | `Previewer.post_process()` 检测 `is_drm` → Toast 提示不支持 |
| **磁盘空间不足** | `_check_disk_space()` 检测 → 抛出 `OSError` → 任务标记为 FAILED |
| **网络超时/断连** | `ChunkWorker` 指数退避重试（最多 5 次）→ 全部失败后任务标记为 FAILED |
| **CDN 数据缩水** | `ChunkWorker` 检查 `downloaded >= expected_size` → 不足触发 `StopIteration` 重试 |
| **HTTP 4xx 不可重试** | `ChunkWorker` 检查 `permanent_status_codes` → 直接标记 FAILED |
| **FFmpeg 合并失败** | `FFmpegRunner.error_signal` → 状态标记 `FFMPEG_FAILED` → 可手动重试 |
| **系统 I/O 错误** | `ChunkWorker` 检查 `permanent_errnos` (权限/磁盘满) → 直接标记 FAILED |
| **下载目录无写入权限** | `MainWindow.check_download_path()` 启动时检查 → Toast 错误提示 |
| **FFmpeg 未找到** | `MainWindow.check_ffmpeg()` 启动时检查 → Toast 错误提示 |
| **重复启动程序** | `QLockFile` 单实例锁 → 激活已有窗口 / 退出 |
| **二维码过期** | 轮询检测 `code == 86038` → 自动重新生成 |

---

## 6. 部署运维指南

### 6.1 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥ 3.9 | 开发与运行 |
| FFmpeg | 任意版本 | 视频合并必需，可通过应用内设置切换来源 |
| 操作系统 | Windows 7+ / Linux (Wayland/X11) / macOS 10.14+ | 跨平台 |

### 6.2 开发环境搭建

```bash
# 1. 克隆仓库
git clone https://github.com/ScottSloan/Bili23-Downloader.git
cd Bili23-Downloader

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt
# 或使用 uv:
# uv pip install -r requirements.txt

# 4. 运行
python src/main.py
```

### 6.3 构建分发

```bash
# pyproject.toml 中定义了项目元数据
name = "bili23-downloader"
version = "2.00.2"

# 构建工具（项目未提供具体构建脚本，需自行配置 PyInstaller/Nuitka）
# 参考 github workflows: .github/workflows/publish.yml
```

**CI/CD**（`.github/workflows/publish.yml`）：GitHub Actions 自动构建发布

**Windows 安装包**：`assets/setup.iss` — Inno Setup 脚本

**macOS 图标**：`assets/app.icns`

### 6.4 数据目录结构

```
{AppData}/Bili23 Downloader/
├── config.json          # 应用配置 (QConfig 自动管理)
├── task.db              # 下载任务数据库 (download_task + completed_task)
├── cover.db             # 封面缓存数据库 (blob 存储)
├── logs/
│   └── app.log          # 按日滚动的应用日志 (保留 15 天)
└── locks/
    └── instance.lock    # 单实例锁文件
```

**AppData 路径**：
- Windows: `C:\Users\{user}\AppData\Roaming\`
- Linux: `~/.local/share/`
- macOS: `~/Library/Application Support/`

### 6.5 配置管理注意事项

- **`QConfig` 自动持久化**：通过 `qconfig.set(config.key, value)` 设置的项会自动保存到 `config.json`
- **敏感数据**：Cookie 信息（`SESSDATA`、`bili_jct` 等）明文存储在配置文件中，需注意保护
- **配置文件损坏处理**：启动时若 `config.json` 不存在，`QConfig` 会使用默认值创建新文件

### 6.6 日志管理

```python
# main.py 日志配置
TimedRotatingFileHandler(
    log_path,           # 文件路径
    when = "midnight",  # 每天午夜轮转
    interval = 1,       # 间隔 1 天
    backupCount = 15,   # 保留 15 天
    encoding = "utf-8"
)
```

日志级别：`INFO`（默认）
日志格式：`[YYYY-MM-DD HH:MM:SS] - module_name - LEVEL: message`

### 6.7 性能参数调优

| 参数 | 默认值 | 调优建议 |
|------|--------|---------|
| `download_thread` (单任务线程数) | 4 (1-10) | 高带宽环境可设为 8-10；低带宽或限速环境建议 2-4 |
| `download_parallel` (并行任务数) | 1 (1-10) | 多任务并行下载，注意总带宽分配 |
| `speed_limit_rate` (限速 MB/s) | 10.0 | 0 = 不限速；建议设为带宽的 70-80% |
| `chunk_size` (分片大小) | 4MB | 硬编码，平衡 HTTP Range 请求开销与并发度 |
| `httpx max_connections` | 10 (全局) / download_thread (单任务) | 通过连接池复用减少 TCP 握手开销 |
| 封面线程池 | 16 | 异步加载封面缩略图 |

---

## 7. 常见问题排查手册

### 7.1 解析相关

| 问题 | 可能原因 | 排查步骤 |
|------|---------|---------|
| **解析失败：无效的链接** | URL 格式不符合任何已知模式 | 检查 URL 是否标准 B 站链接；确认 `url_pattern.py` 中正则表达式覆盖情况 |
| **解析失败：接口请求错误** | API 返回 code != 0；WBI 签名过期 | 查看日志中 API 响应详情；确认 `img_key`/`sub_key` 是否有效；检查 Cookie 是否过期 |
| **解析成功但列表为空** | API 返回数据但无视频内容 | 检查登录态（空间/收藏夹需要登录）；查看视频是否被删除/下架 |
| **互动视频解析卡住** | BFS 遍历陷入循环或 API 限频 | 检查 `visited_states` 去重逻辑；查看 `stop_event` 是否正确触发 |
| **重定向链接处理异常** | B23Parser 解析失败 | 手动访问 b23.tv 短链确认跳转目标；检查 hdrs 请求头 |

### 7.2 下载相关

| 问题 | 可能原因 | 排查步骤 |
|------|---------|---------|
| **下载失败：解析下载链接失败** | `playurl` API 返回异常；Cookie 过期；付费内容 | 检查日志中具体异常；确认 Cookie 有效；确认是否为大会员专享内容 |
| **下载失败：磁盘空间不足** | 目标磁盘剩余空间 < 文件大小 | 清理磁盘或更换下载路径 |
| **下载失败：HTTP 404/403** | 视频链接过期或被删除 | 重新解析获取新的下载链接；链接有效期通常数小时 |
| **下载速度慢** | 网络限速、CDN 节点问题、线程数太少 | 检查 `speed_limit_rate` 设置；切换 CDN 服务器；增加 `download_thread` |
| **下载进度不更新** | ChunkWorker 线程异常但未正确上报 | 检查日志中 chunk 级别异常；查看 `_download_error_triggered` 防抖逻辑 |
| **断点续传失效** | chunks_list 状态与文件实际大小不一致 | 检查 `calc_downloaded_size()` 逻辑；手动删除不完整文件重新下载 |
| **FFmpeg 合并失败** | FFmpeg 未安装/版本过低/临时文件损坏 | 运行 `ffmpeg -version` 确认可用；检查 `config.no_ffmpeg_available`；配置自定义 FFmpeg 路径 |
| **m4a 转 mp3 失败** | FFmpeg 缺少 libmp3lame 编码器 | 安装带 libmp3lame 的 FFmpeg 构建版；或关闭 `m4a_to_mp3` 选项 |

### 7.3 登录相关

| 问题 | 可能原因 | 排查步骤 |
|------|---------|---------|
| **二维码生成失败** | B 站 API 限频；网络不通 | 检查网络连接；稍后重试；查看 `passport.bilibili.com` 可达性 |
| **扫码后无响应** | 轮询间隔内用户未操作；state 判断异常 | 在 APP 中确认授权；刷新二维码重新扫码 |
| **二维码过期** | 超过有效期（通常 3 分钟） | 程序会自动重新生成；手动关闭登录窗口重新打开 |
| **短信验证码发送失败** | 极验验证码未通过；cid 选择错误；手机号格式错误 | 检查地区代码选择；完成滑块验证；确认手机号正确 |
| **登录后 Cookie 立即过期** | 网络时间偏差；Cookie 设置异常 | 检查 `domain=".bilibili.com"` 是否正确；更新系统时间 |
| **已登录但下载需要登录** | SESSDATA 过期 | 检查 Cookie 中 `is_expired` 标记；重新登录 |

### 7.4 程序运行相关

| 问题 | 可能原因 | 排查步骤 |
|------|---------|---------|
| **程序无法启动** | 配置损坏、端口占用、依赖缺失 | 删除 `config.json` 重置配置；检查 `instance.lock`；运行 `pip list` 确认依赖 |
| **提示"程序已在运行"** | 单实例锁未正常释放 | 删除 `{AppData}/Bili23 Downloader/locks/instance.lock`；重启系统 |
| **界面卡顿** | 主线程阻塞（长时间同步操作） | 所有网络 I/O 和耗时操作均已异步化；若出现卡顿检查日志中的同步调用 |
| **封面不显示** | cover.db 损坏；网络请求队列积压 | 删除 `cover.db` 重建；检查封面线程池是否满载 |
| **设置无法保存** | config.json 写入权限问题 | 检查 `{AppData}/Bili23 Downloader/` 目录权限 |
| **系统托盘图标不可见** | 桌面环境不支持系统托盘 | Linux 需安装托盘扩展（如 GNOME AppIndicator）；macOS 通常正常 |
| **HiDPI 缩放异常** | display_scaling 设置不正确 | 尝试设为 Auto 依赖系统缩放；或手动指定具体比例 |

### 7.5 日志分析指南

日志位于 `{AppData}/Bili23 Downloader/logs/app.log`，可通过以下关键词快速定位问题：

| 关键词 | 关联模块 |
|--------|---------|
| `解析失败` | parse 模块异常 |
| `接口请求错误` | B 站 API 返回非 0 code |
| `下载失败` | downloader 异常 |
| `FFmpeg` | 合并/转码问题 |
| `异常状态码` | HTTP 下载错误 |
| `文件读写失败` | 磁盘 I/O 问题 |
| `空间不足` | 磁盘空间检查 |
| `buvid` / `ticket` | Cookie 初始化 |
| `logout` | 登录态过期检测 |
| `instance` | 单实例管理 |

---

## 8. 附录

### 8.1 项目文件清单

```
Bili23-Downloader/
├── src/                                    # 源代码根目录
│   ├── main.py                             # 应用入口（QApplication 子类、日志、单实例锁）
│   ├── gui/                                # GUI 层
│   │   ├── interface/                      # 主界面（3 个页面）
│   │   │   ├── main_window.py              # MainWindow（MSFluentWindow）
│   │   │   ├── parse.py                    # ParseInterface（URL 解析）
│   │   │   ├── download.py                 # DownloadInterface（下载管理）
│   │   │   └── setting.py                  # SettingInterface（设置页面）
│   │   ├── component/                      # 可复用组件
│   │   │   ├── download_list/              # 下载列表（Model/View/Delegate/Proxy/TopWidget）
│   │   │   ├── parse_list/                 # 解析列表（TreeView/Model/Header）
│   │   │   ├── entry_list/                 # 封面网格列表
│   │   │   ├── setting/                    # 设置卡片组件（30+ 种卡片类型）
│   │   │   ├── widget/                     # 基础控件（Avatar/Button/ComboBox/Flyout/InfoBar/
│   │   │   │                               #   Label/List/Navigation/Pager/Pivot/Progress/
│   │   │   │                               #   Scroll/Search/Segment/Spinbox/Tree）
│   │   │   ├── view_model/                 # MVVM 基类（Delegate/Model）
│   │   │   ├── dialog.py                   # 通用对话框基类
│   │   │   ├── profile.py                  # 用户信息卡片
│   │   │   └── sys_tray.py                 # 系统托盘图标
│   │   └── dialog/                         # 对话框
│   │       ├── download_options/           # 下载选项对话框
│   │       ├── setting/                    # 设置子对话框（14 个）
│   │       ├── misc/                       # 杂项对话框（8 个）
│   │       ├── login.py                    # 登录对话框
│   │       └── update.py                   # 更新提示对话框
│   ├── util/                               # 业务逻辑层 + 基础设施层
│   │   ├── parse/                          # 解析引擎
│   │   │   ├── worker.py                   # 解析调度器
│   │   │   ├── parser/                     # 12 个解析器
│   │   │   ├── episode/                    # 13 个剧集构建器
│   │   │   ├── additional/                 # 附加文件（弹幕/字幕/封面/元数据）
│   │   │   └── preview/                    # 媒体预览
│   │   ├── download/                       # 下载引擎
│   │   │   ├── downloader/                 # 下载器子系统
│   │   │   ├── task/                       # 任务管理子系统
│   │   │   ├── cover/                      # 封面管理子系统
│   │   │   └── parse/                      # 下载链接解析
│   │   ├── auth/                           # 认证模块（6 个）
│   │   ├── ffmpeg/                          # FFmpeg 封装（2 个）
│   │   ├── network/                        # 网络层（3 个）
│   │   ├── common/                         # 通用基础设施（15+ 个）
│   │   ├── format/                          # 格式化工具（3 个）
│   │   ├── misc/                            # 杂项（4 个）
│   │   └── thread/                          # 线程管理（3 个）
│   └── res/                                # 资源文件
│       ├── html/       captcha.html        # 极验验证码 WebView
│       ├── i18n/       4 个翻译文件        # 中英繁翻译
│       ├── icon/       60+ SVG 图标        # 亮色/暗色双主题
│       ├── image/      2 个占位图          # 默认头像/缩略图
│       ├── qss/        8 个样式表          # 亮色/暗色双主题
│       └── resources.qrc / resources_rc.py  # Qt 资源文件
├── assets/                                 # 构建资源
│   ├── app.icns                            # macOS 应用图标
│   └── setup.iss                           # Inno Setup 安装脚本 (Windows)
├── scripts/
│   └── translate.py                        # 翻译辅助脚本
├── .github/
│   ├── ISSUE_TEMPLATE/                     # Issue 模板
│   │   ├── bug-report.yml                  # Bug 报告模板
│   │   ├── feature_request.yml             # 功能请求模板
│   │   └── config.yml                      # Issue 配置
│   ├── workflows/
│   │   └── publish.yml                     # GitHub Actions 自动构建发布
│   └── FUNDING.yml                         # 赞助信息
├── pyproject.toml                          # 项目元数据 (PEP 621)
├── requirements.txt                        # pip 依赖列表
├── CHANGELOG.md                            # 版本更新日志
├── README.md                               # 中文项目说明
├── README_en.md                            # 英文项目说明
├── LICENSE                                 # GPL-3.0 许可证
├── .gitignore                              # Git 忽略规则
└── .gitattributes                          # Git 属性配置
```

### 8.2 B 站 API 接口清单

以下是项目中调用的主要 B 站 API 接口：

| API 端点 | 用途 | 所属模块 |
|----------|------|---------|
| `api.bilibili.com/x/web-interface/wbi/view` | 视频信息获取（WBI 签名） | VideoParser |
| `api.bilibili.com/x/player/wbi/playurl` | 投稿视频播放链接获取 | ParseWorker (downloader) |
| `api.bilibili.com/pgc/player/web/playurl` | 番剧视频播放链接获取 | ParseWorker (downloader) |
| `api.bilibili.com/pugv/player/web/playurl` | 课程视频播放链接获取 | ParseWorker (downloader) |
| `api.bilibili.com/pgc/view/web/season` | 番剧/影视季节信息 | BangumiParser |
| `api.bilibili.com/pugv/view/web/season` | 课程信息 | CheeseParser |
| `api.bilibili.com/x/space/wbi/arc/search` | 个人空间视频列表 | SpaceParser |
| `api.bilibili.com/x/v3/fav/resource/list` | 收藏夹内容列表 | FavlistParser |
| `api.bilibili.com/x/polymer/web-space/seasons_series_list` | 合集列表 | ListParser |
| `api.bilibili.com/x/web-interface/popular/series/one` | 每周必看 | PopularParser |
| `api.bilibili.com/x/v2/history/toview/web` | 稍后再看 | WatchLaterParser |
| `api.bilibili.com/x/web-interface/history/cursor` | 历史记录 | HistoryParser |
| `api.bilibili.com/x/polymer/web-dynamic/v1/feed/space` | 动态视频 | DynamicParser |
| `api.bilibili.com/x/stein/edgeinfo_v2` | 互动视频剧情图 | InteractiveVideoParser |
| `passport.bilibili.com/x/passport-login/web/qrcode/generate` | 生成登录二维码 | QRCode |
| `passport.bilibili.com/x/passport-login/web/qrcode/poll` | 轮询二维码状态 | QRCode |
| `passport.bilibili.com/x/passport-login/sms/send` | 发送短信验证码 | SMS |
| `passport.bilibili.com/x/passport-login/sms/login` | 短信验证码登录 | SMS |
| `api.bilibili.com/x/web-interface/nav` | 用户导航信息 | UserManager |
| `api.bilibili.com/x/frontend/finger/spi` | 获取 buvid3/buvid4 | CookieManager |
| `api.bilibili.com/x/player/v2` | 视频分P CID 列表 | 自动选择 |
| `api.bilibili.com/x/player/wbi/v2` | 视频详细信息（含互动视频） | InteractiveVideoParser |

### 8.3 命名约定规则

项目支持 5 种默认命名约定，对应不同内容类型：

| 约定 ID | 名称 | 类型 | 规则 | 示例 |
|---------|------|------|------|------|
| `a024c20c...` | DEFAULT_FOR_NORMAL | 普通视频 (11) | `{leaf_title}` | `【教程】Python入门.mp4` |
| `2d98a265...` | DEFAULT_FOR_PART | 分P视频 (12) | `{parent_title}/P{p}-{leaf_title}` | `合集名/P1-第一集.mp4` |
| `307906bd...` | DEFAULT_FOR_COLLECTION | 合集 (13) | `{collection_title}/{section_title}/{parent_title}/{leaf_title}` | `合集/章节/视频名/分P名.mp4` |
| `b1d4e8e3...` | DEFAULT_FOR_BANGUMI | 番剧 (20) | `{season_title}/{episode_title}` | `番剧名/第1集.mp4` |
| `d582ec37...` | DEFAULT_FOR_CHEESE | 课程 (30) | `{series_title}/{episode_title}` | `课程名/第1课.mp4` |

### 8.4 画质/音质/编码对照表

| 画质 ID | 说明 | 音质 ID | 说明 | 编码 ID | 说明 |
|---------|------|---------|------|---------|------|
| 127 | 8K 超高清 | 30251 | Hi-Res 无损 | 7 | AV1 |
| 126 | 杜比视界 | 30250 | 杜比全景声 | 12 | HEVC (H.265) |
| 125 | HDR 真彩 | 30280 | 320Kbps | 13 | AVC (H.264) |
| 120 | 4K 超清 | 30232 | 128Kbps | | |
| 116 | 1080P 60帧 | 30216 | 64Kbps | | |
| 112 | 1080P 高码率 | | | | |
| 100 | 1080P | | | | |
| 80 | 720P | | | | |
| 64 | 480P | | | | |
| 32 | 360P | | | | |
| 16 | 160P | | | | |

---

> **文档生成日期**: 2026-06-06
> **文档版本**: 1.0
> **基于源码版本**: v2.00.7