from pathlib import Path
from util.common.enum import FileConflictResolution
from util.common import config

from threading import Lock
import logging

logger = logging.getLogger(__name__)

_rename_lock = Lock()

def safe_remove(cwd: str | Path, *file_names: str):
    for file_name in file_names:
        path = Path(cwd, file_name)
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            logger.exception("删除文件 %s 时出错", path)
            raise e


def safe_rename(cwd: str | Path, original_file_name: str, new_file_name: str) -> Path:
    original_path = Path(cwd, original_file_name)
    new_path = Path(cwd, new_file_name)

    if not original_path.exists():
        raise FileNotFoundError(f"原始文件不存在: {original_path}")

    with _rename_lock:
        new_path = __resolve_conflict(original_path, new_path)
        
        try:
            original_path.rename(new_path)
            return new_path
        except Exception as e:
            logger.exception("重命名文件失败: %s -> %s", original_path, new_path)
            raise e


def __resolve_conflict(original_path: Path, new_path: Path) -> Path:
    if not new_path.exists():
        return new_path

    match config.get(config.file_conflict_resolution):
        case FileConflictResolution.OVERWRITE:
            new_path.unlink()
            return new_path

        case FileConflictResolution.AUTO_RENAME:
            suffix = new_path.suffix
            name_without_suffix = new_path.stem

            n = 1
            while True:
                new_name = f"{name_without_suffix} ({n}){suffix}"
                new_target_path = new_path.with_name(new_name)

                if not new_target_path.exists():
                    return new_target_path
                n += 1


class File:
    @staticmethod
    def preallocate_file(path: str, size: int):
        with open(path, "wb") as f:
            f.seek(size - 1)
            f.write(b"\0")
