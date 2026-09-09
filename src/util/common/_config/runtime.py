from .paths import APP_NAME

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
