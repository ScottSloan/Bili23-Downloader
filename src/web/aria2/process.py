"""
aria2c 进程管理

D4 已经写明：切 aria2 的代价是「要像管 ffmpeg 一样内置 aria2c 并管理进程生命周期、
RPC secret、端口占用、崩溃重启」。这个文件就是那份代价。

支持两种形态：

- `aria2_managed = True`（默认）：由本进程拉起 aria2c 并在退出时收掉
- `aria2_managed = False`：连接一个已经在跑的实例（Docker 里把 aria2 拆成 sidecar 时用）

**RPC 令牌不是可选项。** aria2 的 RPC 没有 `--rpc-secret` 就是裸奔的：本机任意进程都能
往里塞下载任务、改下载目录。首次启动会随机生成一个存进配置。
"""

from pathlib import Path
from typing import List, Optional
import logging
import os
import shutil
import socket
import subprocess
import secrets

from util.common.config import config
from util.common._config.paths import get_data_dir

logger = logging.getLogger(__name__)

# aria2 的会话文件。进程重启后据此恢复未完成的任务（S3-8 的对账要用）
SESSION_FILE = "aria2.session"

# aria2 的控制台输出落到这里。**不能用管道**，理由见 Aria2Process._open_log()
LOG_FILE = "aria2.log"

# 日志超过这个大小就轮换一次。aria2 在下载出错时会持续打印，不轮换的话
# 长期运行下这个文件会无限长
MAX_LOG_BYTES = 4 * 1024 * 1024

def ensure_secret() -> str:
    """没有 RPC 令牌就随机生成一个并存起来"""
    secret = config.get(config.aria2_rpc_secret)

    if not secret:
        secret = secrets.token_urlsafe(32)

        config.set(config.aria2_rpc_secret, secret)

        logger.info("已生成 aria2 RPC 令牌")

    return secret

def resolve_executable() -> Optional[str]:
    """定位 aria2c：优先用配置里指定的，其次从 PATH 找"""
    configured = config.get(config.aria2_path)

    if configured:
        path = Path(configured)

        if path.is_file():
            return str(path)

        logger.warning("配置里的 aria2 路径不存在：%s，改从 PATH 查找", configured)

    return shutil.which("aria2c")

class Aria2Process:
    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._log = None

        self.host = config.get(config.aria2_rpc_host)
        self.port = config.get(config.aria2_rpc_port)
        self.secret = ensure_secret()

    @property
    def rpc_url(self) -> str:
        return f"ws://{self.host}:{self.port}/jsonrpc"

    def build_args(self, executable: str) -> List[str]:
        session_path = get_data_dir() / SESSION_FILE

        args = [
            executable,
            "--enable-rpc",
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            # 只听环回：RPC 是给本进程用的，没有理由暴露出去。
            # sidecar 形态下 aria2 由对方启动，不走这里
            "--rpc-listen-all=false",

            # 断点续传。业务层按 D4 只负责挑 URL 与定文件名，续传交给 aria2
            "--continue=true",
            # 出错自动重试，但不要无限重试 —— 失败要能冒到业务层去换 CDN
            "--max-tries=3",
            "--retry-wait=2",

            # 会话文件只用于人工排查，**不作为对账依据**（S3-8）。
            #
            # 实测（Windows）：`Popen.terminate()` 就是 TerminateProcess，aria2 没有机会
            # 跑退出处理，session 根本不会落盘 —— 更别说被强杀或断电的情况。
            # 所以恢复只能以 task.db 为准，见 web/download/reconcile.py
            f"--save-session={session_path}",
            "--auto-save-interval=30",
            "--force-save=false",

            # 控制台不需要进度刷屏。输出量小不代表可以不管它 ——
            # 见 _open_log() 里那段，管道写满会让 aria2 整个卡死
            "--console-log-level=warn",
            "--summary-interval=0",
            "--quiet=false",
        ]

        # **刻意不带 --input-file。** 让 aria2 自己从 session 里把任务捞回来，会与对账时
        # 重新投递的那一份撞在一起：两个下载写同一个文件，且 aria2 不认为这是错误。
        # 恢复统一由 reconcile.py 按 task.db 驱动，aria2 这边保持「只做被交代的事」

        return args

    def _open_log(self):
        """
        给 aria2 的输出开一个日志文件

        **这不是为了留日志，是为了不让它卡死。**

        原先用的是 `stdout = subprocess.PIPE` 且从不读。管道有容量（Windows 上 64KB），
        写满之后 aria2 会永远阻塞在 write 上 —— 内核仍会 accept TCP 连接，
        所以端口看着是通的，但进程再也不处理任何请求。表现出来是
        「keepalive ping timeout」加上无穷无尽的「timed out during opening handshake」，
        完全看不出病因。

        实测：`--console-log-level=debug` 下大约 4 秒就写满并卡死；改成文件后全程正常。

        文件写入不会阻塞，所以只要不是管道就行；用文件而不是 DEVNULL 是为了留下
        启动失败时的诊断信息。
        """
        path = get_data_dir() / LOG_FILE

        try:
            path.parent.mkdir(parents = True, exist_ok = True)

            # 超过上限就截断重来。aria2 在下载出错时会持续打印，不管的话会无限长
            if path.is_file() and path.stat().st_size > MAX_LOG_BYTES:
                path.unlink()

            return open(path, "ab", buffering = 0)

        except Exception:
            logger.exception("无法打开 aria2 日志文件，改用 DEVNULL")

            # 退回 DEVNULL 也比管道强：丢掉诊断信息，但不会把 aria2 卡死
            return subprocess.DEVNULL

    def _close_log(self) -> None:
        log = self._log
        self._log = None

        if log is None or log == subprocess.DEVNULL:
            return

        try:
            log.close()

        except Exception:
            pass

    def _responds(self, timeout: float = 3.0) -> bool:
        """
        端口上那个东西是不是一个还答话的 aria2

        用 HTTP 的 JSON-RPC 探一下就够了，不必开 WebSocket：卡死的进程连 HTTP 都不回，
        而别的程序不会认得 aria2.getVersion
        """
        import json
        import urllib.error
        import urllib.request

        payload = json.dumps({
            "jsonrpc": "2.0", "id": "probe", "method": "aria2.getVersion",
            "params": [f"token:{self.secret}"],
        }).encode()

        request = urllib.request.Request(
            f"http://{self.host}:{self.port}/jsonrpc",
            data = payload, headers = {"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(request, timeout = timeout) as response:
                body = json.loads(response.read())

        except urllib.error.HTTPError as e:
            # 有响应就说明它活着。401 之类是令牌不对 —— 那是另一个问题，
            # 但至少不该按「端口被卡死的进程占着」处理
            logger.warning("aria2 的 RPC 返回 HTTP %s，令牌可能不匹配", e.code)

            return True

        except Exception as e:
            logger.debug("探测 aria2 RPC 无响应：%s", e)

            return False

        return "result" in body or "error" in body

    def port_in_use(self) -> bool:
        """RPC 端口上是否已经有人在听"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.5)

            return probe.connect_ex((self.host, self.port)) == 0

    def start(self) -> bool:
        """拉起 aria2c。已在运行或配置为连接外部实例时直接返回 True"""
        if not config.get(config.aria2_managed):
            logger.info("aria2 由外部管理，跳过启动（RPC：%s）", self.rpc_url)

            return True

        if self._proc is not None and self._proc.poll() is None:
            return True

        # 端口已经有人听着：可能是上次没退干净的孤儿，也可能是别的程序。
        #
        # **孤儿不罕见**：本进程若被强杀（崩溃、任务管理器结束进程），生命周期的收尾代码
        # 没机会跑，上一个 aria2c 就继续占着端口。它多半还是可用的 —— RPC 令牌存在
        # 配置里，重启后仍然对得上，直接复用比再起一个好。
        #
        # **但必须先确认它还答话。** 早先这里是无条件复用的，注释里还写着「令牌不匹配时
        # 客户端会给出明确的鉴权错误」—— 那句是错的：占端口的若是个卡死的进程或别的程序，
        # 得到的是握手超时，而且会一直重连下去，日志里只有一行
        # 「timed out during opening handshake」，看不出病因
        if self.port_in_use():
            if self._responds():
                logger.info("RPC 端口 %d 上已有可用的 aria2，复用它（可能是上次未正常退出留下的）",
                            self.port)

                return True

            logger.error(
                "RPC 端口 %d 被占用，但对方不响应 aria2 的 RPC。"
                "多半是上次残留的 aria2c 卡死了，或该端口被别的程序占用。"
                "请结束占用该端口的进程，或在配置里把 aria2_rpc_port 换一个",
                self.port)

            return False

        executable = resolve_executable()

        if not executable:
            logger.error("找不到 aria2c。请安装后加入 PATH，或在配置里指定 aria2_path")

            return False

        args = self.build_args(executable)

        kwargs = {}

        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        try:
            self._log = self._open_log()

            self._proc = subprocess.Popen(
                args,
                # **绝不能用 subprocess.PIPE**，理由见 _open_log()
                stdout = self._log,
                stderr = subprocess.STDOUT,
                # aria2 不需要 stdin，留着只会在某些终端环境下带来干扰
                stdin = subprocess.DEVNULL,
                **kwargs
            )

        except Exception:
            logger.exception("启动 aria2c 失败：%s", executable)

            self._close_log()

            return False

        logger.info("aria2c 已启动，PID %d，RPC %s", self._proc.pid, self.rpc_url)

        return True

    def is_running_owned(self) -> bool:
        """本对象是否**亲手**拉起了一个仍在运行的 aria2c（区别于复用别人的）"""
        return self._proc is not None and self._proc.poll() is None

    def is_running(self) -> bool:
        if not config.get(config.aria2_managed):
            # 外部实例的存活由 RPC 连接本身反映，这里不猜
            return True

        return self._proc is not None and self._proc.poll() is None

    def read_output(self, limit: int = 4000) -> str:
        """把 aria2 日志的末尾读出来，用于启动失败或异常时的诊断"""
        path = get_data_dir() / LOG_FILE

        if not path.is_file():
            return ""

        try:
            with open(path, "rb") as f:
                size = path.stat().st_size

                f.seek(max(0, size - limit))

                return f.read().decode("utf-8", errors = "replace")

        except Exception:
            return ""

    def stop(self, timeout: float = 5.0) -> None:
        """
        停掉 aria2c

        **terminate 在 Windows 上是硬杀**（TerminateProcess），aria2 没有机会做任何收尾。
        想让它干净退出得先走 RPC 的 forceShutdown，那是调用方的事（见 app.py 的 lifespan）；
        这里只负责收尾，进程还在就 terminate，再不走就 kill
        """
        proc = self._proc
        self._proc = None

        if proc is None or proc.poll() is not None:
            self._close_log()

            return

        try:
            proc.terminate()

            proc.wait(timeout = timeout)

            logger.info("aria2c 已退出")

        except subprocess.TimeoutExpired:
            logger.warning("aria2c 未在 %.1f 秒内退出，强制结束", timeout)

            try:
                proc.kill()
                proc.wait(timeout = 2)

            except Exception:
                pass

        except Exception:
            logger.exception("停止 aria2c 时出错")

        finally:
            self._close_log()
