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

            # 会话持久化：进程重启后能把未完成的任务捞回来（S3-8 对账的基础）
            f"--save-session={session_path}",
            "--auto-save-interval=30",
            # 强制保存包括已完成/出错的任务，否则重启后对不上账
            "--force-save=false",

            # 控制台不需要进度刷屏，日志由业务层统一记
            "--console-log-level=warn",
            "--summary-interval=0",
            "--quiet=false",
        ]

        # 只有存在时才带 --input-file，否则 aria2 会直接报错退出
        if session_path.exists():
            args.append(f"--input-file={session_path}")

        return args

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

        # 端口已经有人听着：直接复用，不要再起一个。
        #
        # **这不是罕见情况**：本进程若被强杀（崩溃、任务管理器结束进程），
        # 生命周期的收尾代码没机会跑，上一个 aria2c 就成了孤儿并继续占着端口。
        # 此时再 spawn 一个只会因为端口冲突失败，而那个孤儿其实是可用的 ——
        # RPC 令牌存在配置里，重启后仍然对得上。
        #
        # 连上去之后如果令牌不匹配（端口被别的程序占了），客户端会给出明确的鉴权错误
        if self.port_in_use():
            logger.info("RPC 端口 %d 已被占用，复用该实例（可能是上次未正常退出留下的）",
                        self.port)

            return True

        executable = resolve_executable()

        if not executable:
            logger.error("找不到 aria2c。请安装后加入 PATH，或在配置里指定 aria2_path")

            return False

        args = self.build_args(executable)

        kwargs = {}

        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        try:
            self._proc = subprocess.Popen(
                args,
                stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT,
                # aria2 不需要 stdin，留着只会在某些终端环境下带来干扰
                stdin = subprocess.DEVNULL,
                text = True,
                encoding = "utf-8",
                errors = "replace",
                **kwargs
            )

        except Exception:
            logger.exception("启动 aria2c 失败：%s", executable)

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

    def read_output(self) -> str:
        """把 aria2 的输出读出来。只在启动失败诊断时用，正常路径不读（会阻塞）"""
        if self._proc is None or self._proc.stdout is None:
            return ""

        try:
            return self._proc.stdout.read() or ""

        except Exception:
            return ""

    def stop(self, timeout: float = 5.0) -> None:
        """
        停掉 aria2c

        先 terminate 让它有机会把 session 落盘 —— 直接 kill 会丢掉未保存的任务状态，
        重启后对不上账
        """
        proc = self._proc
        self._proc = None

        if proc is None or proc.poll() is not None:
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
