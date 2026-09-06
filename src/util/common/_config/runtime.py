"""
运行时状态（不落盘）

config 里混着两类东西，用法不同：持久化项要经 `config.get(item)` 取值，
而这里的属性是普通值，直接读写。两者共处一个对象是历史形态，调用方已有一百多处，
S2-2 不改变这个形态，只是把声明搬出来、顺带把 Qt 依赖摘掉。

**注意：这里的若干项是跨模块可变全局状态，不是单纯的缓存。**
global_starting_number / current_starting_number / target_naming_rule_id /
keep_original_files_type 被 download/task/manager.py 当作全局游标读写（有 += 自增），
mcp/tools/download.py 里已经标注了这里需要互斥。WebUI 后端是另一个进程、另一套并发模型，
这几项到 S3 必须重新设计成请求作用域或显式参数，**不要在此之前给它们加新的读写点**。
"""

from .paths import APP_NAME

# 版本号的唯一来源。另有一份在 pyproject.toml 的 version 字段（commitizen 只改那一处），
# 发布时需手动保持一致 —— 见 CLAUDE.md「版本与发布」。
#
# APP_CONFIG_VERSION 是**配置文件的结构版本**，与程序版本各自独立递增：
# 只有当某次改动需要修补存量用户的 config.json 时才动它，并在 migrate.py 里补一段迁移。
APP_VERSION = "2.15.0"
APP_COMPARABLE_VERSION = "2.15.0"
APP_CONFIG_VERSION = 2150

class RuntimeState:
    # ---- 应用信息 ----
    app_name = APP_NAME
    app_version = APP_VERSION
    app_comparable_version = APP_COMPARABLE_VERSION
    app_config_version = APP_CONFIG_VERSION

    # ---- 登录态 ----
    is_expired = False

    user_uname: str = ""
    user_uid: str = ""

    # GUI 用的是下载好的 QPixmap。这里不加类型注解，避免 core 为了一个恒为 None 的初值
    # 去 import QPixmap —— WebUI 进程里根本没有 QtGui
    user_avatar_pixmap = None

    # 头像的原始地址。WebUI 那边用不了 QPixmap，直接把地址给前端让浏览器自己加载
    # （页面已设 referrer = no-referrer）
    user_face_url: str = ""

    # ---- FFmpeg ----
    ffmpeg_executable = ""
    bundle_ffmpeg_exist = False

    no_ffmpeg_available = True

    # ---- 下载选项 ----
    video_quality_id = 200
    audio_quality_id = 30300
    video_codec_id = 20

    download_video_stream = True
    download_audio_stream = True
    merge_video_audio = True
    keep_original_files = False
    keep_original_files_type = 0

    # ---- MCP 运行时状态，仅供界面展示 ----
    mcp_running = False
    mcp_last_error = ""

    # ---- 杂项 ----
    target_naming_rule_id = None
    global_starting_number = 1
    current_starting_number = None

    main_window_ready = False
