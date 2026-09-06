"""
单实例锁

GUI 与 WebUI **抢同一把锁**：两者共用 config.json、task.db 与下载目录，同时跑起来会互相
覆盖配置、并发写同一个数据库、甚至往同一个文件写两份内容。锁里记着持有者是哪一边，
所以第二个实例能给出「桌面版正在运行」这样具体的提示，而不是干巴巴一句「已在运行」。

**不依赖 Qt。** 原实现用的是 `QLockFile`，而 `--web-ui` 的分流必须发生在导入任何 Qt 之前
（见 PLAN 的 S2-8），那时候还拿不到 QLockFile。

## 为什么用操作系统的文件锁而不是 PID 文件

`QLockFile` 的思路是「写 PID 进文件 + 超时判定陈旧」，本项目设的 stale 时间是 10 秒。
它有两个毛病：程序崩溃后要干等 10 秒才能重开；而这 10 秒里若 PID 被系统复用给了别的进程，
判定还会出错。

改用 `msvcrt.locking` / `fcntl.flock` 之后，锁由内核持有，**进程一死立即释放**，
不需要任何超时启发式。已实测：持有者被强杀后，下一个进程马上就能拿到锁。

## 文件布局

第 0 字节只用来加锁，持有者信息（JSON）写在它后面。这样安排是因为 Windows 上
`msvcrt.locking` 是**强制锁**：被锁住的字节范围连读都读不了。只锁一个字节，
其余部分就还能被第二个实例读出来用于提示。POSIX 的 flock 是劝告锁，不受影响。
"""

from pathlib import Path
from typing import Optional
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

# 锁文件名。GUI 与 WebUI 共用，不要为某一边另起一个
INSTANCE_LOCK_NAME = "instance.lock"

MODE_GUI = "gui"
MODE_WEBUI = "webui"

MODE_LABELS = {
    MODE_GUI: "桌面版",
    MODE_WEBUI: "WebUI",
}

def _lock_byte(file) -> None:
    """对第 0 字节加非阻塞排他锁，拿不到就抛 OSError"""
    file.seek(0)

    if os.name == "nt":
        import msvcrt

        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)

    else:
        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

def _unlock_byte(file) -> None:
    file.seek(0)

    if os.name == "nt":
        import msvcrt

        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)

    else:
        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_UN)

class InstanceLock:
    def __init__(self, path: Path, mode: str):
        self.path = Path(path)
        self.mode = mode

        self._file = None

    def acquire(self) -> bool:
        """
        尝试取得锁。成功返回 True，已被占用返回 False

        取得之后**必须一直持有文件句柄**，锁是跟着句柄走的
        """
        if self._file is not None:
            return True

        try:
            self.path.parent.mkdir(parents = True, exist_ok = True)

        except Exception:
            logger.exception("创建锁目录失败：%s", self.path.parent)

            # 目录建不出来时不要拦住程序启动 —— 单实例是便利功能，不是正确性前提
            return True

        try:
            # a+b：不存在就创建，存在则保留内容（第二个实例还要读里面的持有者信息）
            file = open(self.path, "a+b")

        except OSError:
            logger.exception("打开锁文件失败：%s", self.path)

            return True

        try:
            # 文件是空的时候先垫一个字节出来，否则没有第 0 字节可锁
            file.seek(0, os.SEEK_END)

            if file.tell() == 0:
                file.write(b"\0")
                file.flush()

            _lock_byte(file)

        except OSError:
            # 已被别的实例持有
            file.close()

            return False

        except Exception:
            logger.exception("获取实例锁时发生意外错误：%s", self.path)

            file.close()

            return True

        self._file = file

        self._write_holder()

        return True

    def _write_holder(self) -> None:
        payload = json.dumps({
            "pid": os.getpid(),
            "mode": self.mode,
            "started_at": time.time(),
        }).encode("utf-8")

        try:
            # 第 0 字节留给锁，信息从第 1 字节开始
            self._file.seek(1)
            self._file.truncate(1)
            self._file.write(payload)
            self._file.flush()

        except Exception:
            # 写不进去只影响提示信息的丰富程度，锁本身已经拿到了
            logger.exception("写入实例信息失败：%s", self.path)

    def read_holder(self) -> Optional[dict]:
        """
        读出当前持有者的信息，读不到返回 None

        供**没抢到锁**的那个实例用来生成提示。注意返回的内容来自另一个进程，
        字段缺失或不合预期都要能容忍
        """
        try:
            with open(self.path, "rb") as file:
                file.seek(1)

                raw = file.read()

        except OSError:
            return None

        if not raw:
            return None

        try:
            data = json.loads(raw.decode("utf-8"))

        except Exception:
            return None

        return data if isinstance(data, dict) else None

    def describe_holder(self) -> str:
        """给用户看的一句话，说明是哪一边占着"""
        holder = self.read_holder()

        if not holder:
            return "另一个实例正在运行"

        label = MODE_LABELS.get(holder.get("mode"), "另一个实例")
        pid = holder.get("pid")

        return f"{label}正在运行" + (f"（PID {pid}）" if pid else "")

    def release(self) -> None:
        file = self._file
        self._file = None

        if file is None:
            return

        try:
            _unlock_byte(file)

        except Exception:
            # 关闭句柄本身也会释放锁，解不开不影响结果
            pass

        try:
            file.close()

        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()

        return False
