# Bili23 Downloader CLI 使用文档

基于 Bili23-Downloader 项目核心模块构建的命令行接口，支持视频/音频/字幕/弹幕/封面下载，无需启动 GUI。

---

## 目录

- [基本语法](#基本语法)
- [功能一：下载视频 (默认)](#功能一下载视频-默认)
- [功能二：仅下载视频流](#功能二仅下载视频流)
- [功能三：仅下载音频](#功能三仅下载音频)
- [功能四：仅下载字幕](#功能四仅下载字幕)
- [功能五：下载弹幕](#功能五下载弹幕)
- [功能六：下载封面](#功能六下载封面)
- [全局可选参数](#全局可选参数)
- [质量 ID / 编码 ID 速查表](#质量-id--编码-id-速查表)
- [异常场景与排查](#异常场景与排查)

---

## 基本语法

```bash
python -m cli [options] <url>
```

| 组成部分 | 说明 |
|---------|------|
| `python -m cli` | 从 `src/` 目录以模块形式运行 CLI |
| `[options]` | 零个或多个可选参数，控制下载行为 |
| `<url>` | 必填，B 站资源地址 |

**URL 支持的格式：**

| 格式 | 示例 |
|------|------|
| 完整视频链接 | `https://www.bilibili.com/video/BV1xx411c7mD` |
| 带分 P 的链接 | `https://www.bilibili.com/video/BV1xx411c7mD?p=2` |
| 番剧 / 课程链接 | `https://www.bilibili.com/bangumi/play/ep12345` |
| b23.tv 短链 | `https://b23.tv/abcd1234` |
| 纯 BV 号 | `BV1xx411c7mD` |
| av 号 | `av170001` |

---

## 功能一：下载视频 (默认)

下载视频及其音频，自动合并为 MP4 文件。

### 语法

```bash
python -m cli [-q <质量ID>] [--codec <编码ID>] [-o <输出目录>] [全局参数] <url>
```

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `<url>` | string | 是 | - | B 站视频地址 |
| `-q`, `--quality` | int | 否 | `200` (自动) | 视频质量 ID，见[速查表](#质量-id--编码-id-速查表) |
| `--codec` | int | 否 | `20` (自动) | 视频编码 ID，见[速查表](#质量-id--编码-id-速查表) |
| `-o`, `--output` | path | 否 | 配置中下载目录 | 输出目录 |

### 返回值

| 退出码 | 含义 |
|--------|------|
| `0` | 下载成功 |
| `1` | 解析或下载失败 |
| `130` | 用户中断 (Ctrl+C) |

### 示范案例

```bash
# 基础下载，自动选择最佳画质和编码
python -m cli "https://www.bilibili.com/video/BV1xx411c7mD"

# 指定 1080P60 + HEVC 编码，输出到 ~/Videos
python -m cli -q 116 --codec 12 -o ~/Videos "https://www.bilibili.com/video/BV1xx411c7mD"

# 下载指定分 P
python -m cli "https://www.bilibili.com/video/BV1xx411c7mD?p=3"

# 使用纯 BV 号
python -m cli -q 80 "BV1xx411c7mD"
```

### 执行流程

```
解析 URL → 获取播放链接 → 选择最佳视频/音频流 → 多线程分片下载 → FFmpeg 合并 → 输出 MP4
```

下载时显示实时进度条：

```
  [████████████░░░░░░░░░░░░░░░░░░]  42%  15.3 MB / 36.1 MB
```

---

## 功能二：仅下载视频流

仅下载视频流（不含音频），不执行合并操作。

### 语法

```bash
python -m cli --video-only [--no-merge] [-q <质量ID>] [-o <输出目录>] <url>
```

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--video-only` | flag | 是 | - | 启用仅视频模式 |
| `--no-merge` | flag | 否 | 关闭 | 不合并，保留原始流文件 (`.m4s` / `.mp4` / `.flv`) |
| `-q`, `--quality` | int | 否 | `200` | 视频质量 ID |
| `<url>` | string | 是 | - | B 站视频地址 |

> 注：指定 `--no-merge` 后保留原始格式文件（DASH 为 `.m4s`，MP4/FLV 为对应格式）。不指定时自动重命名为 `.mp4`。

### 示范案例

```bash
# 仅下载视频流，不下载音频
python -m cli --video-only --no-merge "https://www.bilibili.com/video/BV1xx411c7mD"

# 仅下载视频流并重命名为 mp4
python -m cli --video-only "https://www.bilibili.com/video/BV1xx411c7mD"
```

---

## 功能三：仅下载音频

仅下载音频流，不下载视频。支持可选转码为 MP3。

### 语法

```bash
python -m cli --audio-only [--audio-quality <音频ID>] [--m4a-to-mp3] [-o <输出目录>] <url>
```

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--audio-only` | flag | 是 | - | 启用仅音频模式 |
| `--audio-quality` | int | 否 | `30300` (自动) | 音频质量 ID，见[速查表](#质量-id--编码-id-速查表) |
| `--m4a-to-mp3` | flag | 否 | 关闭 | 下载后将 m4a 转为 mp3（需 FFmpeg） |

### 示范案例

```bash
# 仅下载音频，自动选择最佳音质
python -m cli --audio-only "https://www.bilibili.com/video/BV1xx411c7mD"

# 指定 Hi-Res 音质并转为 mp3
python -m cli --audio-only --audio-quality 30251 --m4a-to-mp3 "https://www.bilibili.com/video/BV1xx411c7mD"

# 指定 192K 音质
python -m cli --audio-only --audio-quality 30280 -o ~/Music "https://www.bilibili.com/video/BV1xx411c7mD"
```

---

## 功能四：仅下载字幕

不下载视频/音频，仅获取字幕文件。这是最快的字幕获取方式。

### 语法

```bash
python -m cli --subtitle-only [--subtitle-type <格式>] [-o <输出目录>] [--force] <url>
```

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--subtitle-only` | flag | 是 | - | 启用仅字幕模式 |
| `-t`, `--subtitle-type` | choices | 否 | `json` | 字幕格式：`json` `srt` `lrc` `txt` `ass` |
| `--force` | flag | 否 | 关闭 | 强制覆盖已存在的字幕文件 |

### 字幕格式说明

| 格式 | 文件扩展名 | 特点 |
|------|-----------|------|
| `json` (默认) | `.json` | B 站原始字幕数据结构，包含完整时间戳和内容 |
| `srt` | `.srt` | 标准字幕格式，广泛兼容播放器 |
| `lrc` | `.lrc` | 歌词格式，适合音乐类内容 |
| `txt` | `.txt` | 纯文本，仅包含字幕内容 |
| `ass` | `.ass` | 高级字幕格式，支持样式定义 |

### 输出文件命名

```
{视频标题}.Subtitles.{语言代码}.{扩展名}

示例:
  TestVideo.Subtitles.zh.json
  TestVideo.Subtitles.en.srt
  TestVideo.Subtitles.ai-zh.ass
```

### 示范案例

```bash
# 下载字幕，默认 JSON 格式
python -m cli --subtitle-only "https://www.bilibili.com/video/BV1xx411c7mD"

# 下载 SRT 格式字幕
python -m cli --subtitle-only -t srt "https://www.bilibili.com/video/BV1xx411c7mD"

# 下载 ASS 格式到指定目录
python -m cli --subtitle-only -t ass -o ~/Subtitles "https://www.bilibili.com/video/BV1xx411c7mD"

# 强制覆盖已存在的字幕
python -m cli --subtitle-only --force "https://www.bilibili.com/video/BV1xx411c7mD"
```

### 执行流程

```
解析 URL → 获取视频信息 → 获取字幕列表 → 展示可用语言 → 逐语言下载 → 格式转换 → 写入文件
```

示例输出：

```
  ============================================================
  字幕下载模式
  ============================================================

  视频: Test Video Title
  输出: /Users/xxx/Downloads
  格式: SRT

  获取字幕列表...

  可用字幕 (3 种):
    - zh (中文（简体）)
    - en (英语)
    - ai-zh (中文（自动生成）)

  [zh] ✓ Test_Video_Title.Subtitles.zh.srt
  [en] ✓ Test_Video_Title.Subtitles.en.srt
  [ai-zh] ✓ Test_Video_Title.Subtitles.ai-zh.srt

  完成: 成功 3/3 种语言
  ============================================================
```

---

## 功能五：下载弹幕

下载视频弹幕（可独立使用或配合视频下载使用）。

### 语法

```bash
python -m cli [--subtitle-only] --danmaku [--danmaku-type <格式>] <url>
```

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--danmaku` | flag | 是 | - | 启用弹幕下载 |
| `--danmaku-type` | choices | 否 | `ass` | 弹幕格式：`ass` `xml` `json` |

### 示范案例

```bash
# 下载视频的同时下载弹幕
python -m cli --danmaku "https://www.bilibili.com/video/BV1xx411c7mD"

# 下载 XML 格式弹幕（与视频一同）
python -m cli --danmaku --danmaku-type xml "https://www.bilibili.com/video/BV1xx411c7mD"

# 仅下载弹幕（配合 --subtitle-only 跳过视频下载）
python -m cli --subtitle-only --danmaku "https://www.bilibili.com/video/BV1xx411c7mD"
```

> 注意：当前版本 `--danmaku` 需配合 `--subtitle-only` 才能实现独立弹幕下载。单独使用 `--danmaku` 仅供 `--subtitle-only` 模式识别。

---

## 功能六：下载封面

下载视频封面图。

### 语法

```bash
python -m cli [--subtitle-only] --cover <url>
```

### 示范案例

```bash
# 下载视频的同时下载封面
python -m cli --cover "https://www.bilibili.com/video/BV1xx411c7mD"

# 仅下载封面
python -m cli --subtitle-only --cover "https://www.bilibili.com/video/BV1xx411c7mD"
```

---

## 全局可选参数

以下参数适用于所有功能模式。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-o`, `--output` | path | 系统下载目录 | 指定输出目录，目录不存在时自动创建 |
| `--threads` | int | `4` | 下载线程数，范围 1-10。更多线程可能加快下载，但也会增加带宽压力 |
| `--speed-limit` | int | `0` (不限) | 下载限速，单位 MB/s。`0` 表示不限制 |
| `--force` | flag | 关闭 | 强制覆盖已存在的文件，否则自动跳过已有文件 |
| `--quiet` | flag | 关闭 | 安静模式，仅输出错误信息 |

### 示范案例

```bash
# 8 线程下载，限速 5 MB/s
python -m cli --threads 8 --speed-limit 5 "https://www.bilibili.com/video/BV1xx411c7mD"

# 强制覆盖 + 自定义输出目录
python -m cli --force -o ~/Videos/Bilibili "https://www.bilibili.com/video/BV1xx411c7mD"

# 安静模式
python -m cli --quiet "https://www.bilibili.com/video/BV1xx411c7mD"
```

---

## 质量 ID / 编码 ID 速查表

### 视频质量 (`-q` / `--quality`)

| ID | 名称 | 分辨率 |
|----|------|--------|
| `200` | 自动 | 自动选择最佳可用画质 |
| `127` | 8K | 7680×4320 |
| `126` | 杜比视界 | - |
| `125` | HDR | - |
| `120` | 4K 超清 | 3840×2160 |
| `116` | 1080P 60帧 | 1920×1080 |
| `112` | 1080P 高码率 | 1920×1080 |
| `80` | 1080P | 1920×1080 |
| `64` | 720P | 1280×720 |
| `48` | 720P | 1280×720 |
| `32` | 480P | 640×480 |
| `16` | 360P | 640×360 |

### 视频编码 (`--codec`)

| ID | 名称 | 特点 |
|----|------|------|
| `20` | 自动 | 按用户配置优先级自动选择 |
| `7` | AVC / H.264 | 兼容性最好 |
| `12` | HEVC / H.265 | 更高压缩比，同等画质文件更小 |
| `13` | AV1 | 最新编码标准 |

### 音频质量 (`--audio-quality`)

| ID | 名称 | 码率 |
|----|------|------|
| `30300` | 自动 | 按用户配置优先级自动选择 |
| `30251` | Hi-Res 无损 | FLAC |
| `30250` | 杜比全景声 | E-AC-3 |
| `30280` | 高音质 | 192 Kbps |
| `30232` | 中音质 | 132 Kbps |
| `30216` | 标准音质 | 64 Kbps |

---

## 异常场景与排查

### 1. 配置文件不存在

**表现：**

```
[HH:MM:SS] WARNING: 配置文件不存在，使用默认配置
```

**原因：** 首次使用，未运行过 GUI 版本生成配置文件。

**排查：**
- 运行一次 Bili23-Downloader GUI 版本，程序会自动创建 `config.json`
- 或者确认环境中存在有效的配置文件

**影响：** 程序会使用内置默认值运行，大部分功能正常，但自定义设置（如下载路径、画质优先级）缺失。

---

### 2. WBI 密钥初始化失败

**表现：**

```
[HH:MM:SS] WARNING: WBI 密钥获取失败: ...
```

**原因：** 无法访问 `api.bilibili.com`，或网络环境异常。

**排查：**
- 检查网络连接：`ping api.bilibili.com`
- 检查是否使用代理且代理配置正确
- 检查防火墙规则

---

### 3. 无法提取 BV 号

**表现：**

```
[HH:MM:SS] ERROR: 无法从 URL 提取 BV 号: xxx
```

**原因：** 输入的 URL 格式不合法，无法解析出 BV 号或 av 号。

**排查：**
- 检查 URL 是否完整有效：`https://www.bilibili.com/video/BV...`
- 确认链接指向的是视频页面而非用户主页或其他页面
- 对于纯 BV 号，确认前缀 `BV` 和后续字符完整

---

### 4. 无法获取视频信息

**表现：**

```
[HH:MM:SS] ERROR: [获取视频信息] 失败 (已重试 3 次): API code=-xxx: ...
```

**原因：**
- 视频已删除或不存在
- 视频仅限大会员/特定区域
- 网络连接不稳定

**排查：**
- 在浏览器中打开原链接确认视频可正常播放
- 检查是否已登录 B 站（cookies 是否有效）
- 稍后重试

---

### 5. 无法获取播放链接

**表现：**

```
获取播放链接失败 (已重试 3 次): API code=-10403: 大会员专享限制
```

**原因：**
- 视频/番剧需要大会员权限
- 视频存在区域限制
- Cookie 过期或无效

**排查：**
- 确认账号已登录且拥有对应权限
- 运行一次 GUI 版本并扫码登录，确保 cookie 有效
- 对于区域限制的内容，使用代理后重试

---

### 6. 该视频没有字幕

**表现：**

```
该视频没有字幕
```

**原因：** 视频上传者未提供字幕文件，或字幕尚未生成（AI 字幕需要一定时间）。

**排查：**
- 在 B 站网页播放器中检查是否有字幕选项
- 部分视频存在 AI 自动生成字幕，但生成有延迟
- 确认为无字幕视频时，此为正常现象

---

### 7. FFmpeg 不可用

**表现：**

```
FFmpeg 不可用，无法合并。请检查 FFmpeg 安装。
```

**原因：** 系统未安装 FFmpeg，或 FFmpeg 不在 PATH 环境变量中。

**排查：**
- 安装 FFmpeg：`brew install ffmpeg`（macOS）或从 [ffmpeg.org](https://ffmpeg.org) 下载（Windows）
- 确保 `ffmpeg` 在 PATH 中：`ffmpeg -version`
- 或者使用 `--no-merge` / `--audio-only` 模式（无需 FFmpeg）

---

### 8. 分片下载失败

**表现：**

```
[HH:MM:SS] ERROR: 下载失败: 分片 3 下载失败: HTTP 503
```

**原因：** CDN 服务器临时故障或网络中断。

**排查：**
- 程序内置 5 次指数退避重试，通常可自动恢复
- 如果持续失败，检查网络稳定性
- 尝试使用 `--threads 1` 降低并发
- 更换网络环境后重试

---

### 9. 用户中断

**表现：**

```
用户取消下载
```

**退出码：** `130`

**原因：** 用户按下 `Ctrl+C` 主动终止。

**说明：** 部分下载的分片文件会保留在输出目录，重新运行相同命令可基于已有文件继续下载（对于超大文件效果有限，建议删除不完整的文件后重试）。

---

### 10. Python 版本不兼容

**表现：**

```
SyntaxError: invalid syntax (match ...)
```

**原因：** 当前 Python 版本低于 3.10，`match` 语句不可用。

**排查：**
- 升级 Python：`brew install python@3.11`（macOS）
- CLI 代码本身已做兼容处理，不直接使用 `match`，但项目依赖模块（如 `util.ffmpeg`）可能要求 3.10+
- 推荐使用 Python 3.10 或更高版本
