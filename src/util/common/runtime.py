"""
进程级运行时状态。

这些值描述的是"本次运行到目前为止发生了什么"，不落盘、重启即归零，
与 config.py 中那些需要持久化的用户设置是两回事。

把它们从 APPConfig 上分出来，解决的是一个具体的出错来源：过去两类状态
挂在同一个对象上，写法却长得几乎一样 ——

    config.set(config.download_thread, 4)   # 立即写入磁盘
    config.video_quality_id = 127           # 只活在内存里

第二种写法看上去也像在改配置，实际重启就没了。分开之后，
凡是 `config.set(...)` 必定持久化，凡是 `runtime.*.x = ...` 必定不持久化，
两者在字面上再也不会被混淆。

本模块刻意不导入任何东西（包括 Qt），因此可以被任何层安全导入，
不会引入循环依赖，也不会把 Qt 拖进不需要它的调用路径。
"""


class AuthState:
    """登录态。用户信息在登录成功或启动时的鉴权回调中写入"""

    def __init__(self):
        # Cookie 仍在但已失效（与"从未登录"不同，需要提示用户重新登录）
        self.is_expired = False

        self.uname: str = ""
        self.uid: str = ""

        # QPixmap。此处不做类型标注，以免为了一个注解把 QtGui 拖进本模块
        self.avatar_pixmap = None


class FFmpegState:
    """FFmpeg 的可用性探测结果，在启动时由 util.ffmpeg 写入一次"""

    def __init__(self):
        self.executable: str = ""
        self.bundle_exist: bool = False

        # 既没有内置也没有找到外部可执行文件
        self.unavailable: bool = True


class DownloadOptionsState:
    """
    下载选项对话框中当前选定的值。

    这些是"下一个任务用什么参数"的暂存，创建任务时会被固化进 TaskInfo，
    此后修改不再影响已入队的任务（2.15.0 起的行为）。
    """

    def __init__(self):
        self.video_quality_id: int = 200
        self.audio_quality_id: int = 30300
        self.video_codec_id: int = 20

        self.download_video_stream: bool = True
        self.download_audio_stream: bool = True
        self.merge_video_audio: bool = True

        self.keep_original_files: bool = False
        self.keep_original_files_type: int = 0


class MCPState:
    """MCP 服务器的运行状况，仅供设置界面展示"""

    def __init__(self):
        self.running: bool = False
        self.last_error: str = ""


class NamingState:
    """命名规则与编号的本次选择"""

    def __init__(self):
        # 本次下载为各内容类型选定的规则：{ConventionType: rule_id}。
        # 一次解析里可能混有多种类型，只记一个 id 的话，它会被无差别套给整批任务
        self.target_rule_ids: dict = {}

        # 全局起始序号；current 为本次解析的临时覆盖，None 表示沿用 global
        self.global_starting_number: int = 1
        self.current_starting_number = None


class AppState:
    """应用生命周期标记"""

    def __init__(self):
        # 主窗口是否已就绪。signal_bus 据此决定信号是直接发出还是先排队
        self.main_window_ready: bool = False


class RuntimeState:
    def __init__(self):
        self.auth = AuthState()
        self.ffmpeg = FFmpegState()
        self.download = DownloadOptionsState()
        self.mcp = MCPState()
        self.naming = NamingState()
        self.app = AppState()


runtime = RuntimeState()
