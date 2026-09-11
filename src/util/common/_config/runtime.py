from .paths import APP_NAME

APP_VERSION = "2.20.0"
APP_COMPARABLE_VERSION = "2.20.0"
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
    # 下载选项对话框里选中的命名规则。**它只是个默认值**：建任务时会被
    # snapshot() 固化进 TaskInfo.Options，之后一律读那一份 ——
    # 否则用户中途重新解析一条链接（预览器会把这里清成 None），
    # 队列里还没开始的任务落盘时就换成默认规则了
    target_naming_rule_id = None

    # 「全局顺序编号」的计数器。语义就是一个进程会话内跨批次连续累加，
    # 因此它保持全局；「每批从 1 开始」那一档已改成按 numbering_batch_id 分批，
    # 原先那个 current_starting_number 全局游标随之删除
    global_starting_number = 1

    main_window_ready = False
