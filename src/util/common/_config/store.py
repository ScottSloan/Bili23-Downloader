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
