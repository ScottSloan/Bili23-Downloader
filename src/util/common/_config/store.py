"""
config.json 的读写

三件事必须做对，缺一样都会丢用户数据：

1. **未知字段透传**（D5）。GUI 与 WebUI 共用一份 config.json，一边写盘时不能把另一边的字段
   抹掉。旧实现丢字段的根因是 `QConfig.toDict()` 用 `dir(cls)` 反射收集所有 ConfigItem，
   类里没声明的键一律不写回 —— `QFluentWidgets` 段（主题、强调色、字体）也在此列，
   所以那一段同样要靠透传保住，这与 D5 是同一条要求而不是两条。

2. **原子替换**。就地截断写一旦中途被打断，留下的是残缺文件，用户全部设置随之丢失；
   而退出流程走的是 os._exit，不会等待仍在写盘的线程。旧实现已经这么做了，照搬。

3. **写盘串行化**。config.set() 默认立即触发写盘，而登录相关的请求回调各自跑在自己的
   工作线程上（cookie_manager.init_cookie_info 启动时会并发发出三个请求），
   两个线程同时写同一个文件会写出互相交错的内容。旧实现用线程锁解决，照搬。

透传的实现方式是**保存时重新读盘再合并**，而不是「记住加载时看到的未知字段」。
这样即使另一个进程在我们运行期间往文件里加了字段，也不会被我们下一次保存抹掉。
跨进程的并发写本身由单实例锁（S2-7）挡住，两者不冲突：单实例锁保证不会同时跑，
读改写保证即使真的错开跑了也不丢数据。
"""

from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

# 替换失败后的重试次数与间隔。总等待上限约 250ms —— 对一次配置保存而言无感，
# 而正常的读取方（启动时读一次）远用不了这么久
_REPLACE_RETRIES = 10
_REPLACE_BACKOFF = 0.025

def _replace_with_retry(temp_path: Path, target: Path) -> None:
    """
    原子替换，失败时短暂重试

    Windows 上 os.replace 要求目标文件没有被别人打开（除非对方带了 FILE_SHARE_DELETE），
    否则抛 PermissionError / WinError 5。另一个进程正好在读 config.json 就会撞上 ——
    GUI 与 WebUI 共用同一份配置（D5）之后，这种同时读写会成为常态。

    这不是数据损坏（临时文件是完整的，目标文件也没被动过），只是这一次保存没落地。
    但用户的感受是「设置改了没生效」，所以值得重试几次。
    POSIX 上 rename 没有这个限制，重试逻辑不会被触发
    """
    for attempt in range(_REPLACE_RETRIES):
        try:
            os.replace(temp_path, target)

            return

        except PermissionError:
            if attempt == _REPLACE_RETRIES - 1:
                # 重试到头仍失败：目标文件被长时间占用。抛出去让调用方记日志并返回 False，
                # **绝不退化成就地覆写** —— 那才是会写出残缺配置文件的做法
                raise

            time.sleep(_REPLACE_BACKOFF)

class ConfigStore:
    def __init__(self, path: Path):
        self.path = path

        self._lock = Lock()

    def load(self) -> dict:
        """
        读出原始 JSON。文件不存在或内容损坏都返回空字典 —— 配置读不出来不该拦住程序启动，
        但**必须留下日志**：旧实现靠 qfluentwidgets 的 @exceptionHandler 把异常静默吞掉，
        用户的配置悄悄回落成默认值而没有任何痕迹
        """
        if not self.path.exists():
            logger.info("配置文件不存在，将使用默认配置：%s", self.path)

            return {}

        try:
            with open(self.path, "r", encoding = "utf-8") as f:
                data = json.load(f)

        except Exception:
            logger.exception("配置文件读取失败，本次使用默认配置（原文件保持不动）：%s", self.path)

            return {}

        if not isinstance(data, dict):
            logger.error("配置文件的顶层不是对象，本次使用默认配置：%s", self.path)

            return {}

        return data

    def save(self, known: dict[str, dict[str, Any]], adjust = None) -> bool:
        """
        把 known（{group: {key: value}}）合并进磁盘上的现有内容后整体写回

        磁盘上有、而 known 里没有的键一律原样保留 —— 这就是未知字段透传。

        adjust 是可选的钩子，签名为 (merged, on_disk) -> None，在写盘前调用，
        用于「需要同时看到磁盘旧值和待写新值」的处理（配置结构版本的降级保护就是这么做的）。
        放在这里是为了让一次保存只读一次盘。

        返回是否写入成功
        """
        with self._lock:
            on_disk = self.load()

            merged = deepcopy(on_disk)

            for group, values in known.items():
                section = merged.get(group)

                if not isinstance(section, dict):
                    section = {}

                    merged[group] = section

                section.update(values)

            if adjust is not None:
                try:
                    adjust(merged, on_disk)

                except Exception:
                    logger.exception("保存前的调整钩子执行失败，按未调整的内容写入")

            return self._write(merged)

    def write(self, data: dict) -> bool:
        """整体覆盖写。不做透传合并，仅供「导出配置」这类明确要写一份干净文件的场景使用"""
        with self._lock:
            return self._write(data)

    def _write(self, data: dict) -> bool:
        try:
            self.path.parent.mkdir(parents = True, exist_ok = True)

            # 先写临时文件再原子替换，避免写到一半被打断留下残缺配置
            temp_path = self.path.parent / f"{self.path.name}.tmp"

            try:
                with open(temp_path, "w", encoding = "utf-8") as f:
                    json.dump(data, f, ensure_ascii = False, indent = 4)

                _replace_with_retry(temp_path, self.path)

                return True

            except Exception:
                logger.exception("保存配置文件失败：%s", self.path)

                try:
                    temp_path.unlink(missing_ok = True)

                except Exception:
                    pass

                return False

        except Exception:
            logger.exception("创建配置目录失败：%s", self.path.parent)

            return False
