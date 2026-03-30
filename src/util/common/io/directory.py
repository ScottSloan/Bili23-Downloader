from PySide6.QtWidgets import QFileDialog, QWidget

from util.format import Units

from shutil import disk_usage
from pathlib import Path
import subprocess
import ctypes
import sys
import os

class Directory:
    @staticmethod
    def ensure_directory_accessible(directory: str) -> bool:
        try:
            path = Path(directory)

            # 目录不存在则创建
            path.mkdir(parents = True, exist_ok = True)

            # 创建临时文件 .access_test 验证目录是否可写
            test_file = path / ".access_test"

            try:
                test_file.touch(exist_ok = True)
                # 删除测试文件
                test_file.unlink()

                return True

            except (OSError, PermissionError):
                return False

        except (OSError, PermissionError, FileNotFoundError):
            return False
        
    @staticmethod
    def calc_disk_space(directory: str) -> str:
        try:
            total, used, free = disk_usage(directory)

            return {
                "total": Units.format_file_size(total),
                "used": Units.format_file_size(used),
                "free": Units.format_file_size(free)
            }

        except (OSError, FileNotFoundError):
            return False
        
    @staticmethod
    def browse_directory(parent: QWidget, title: str, default_path: str = ""):
        dir_path = QFileDialog.getExistingDirectory(parent, title, default_path, QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks)

        if dir_path:
            try:
                if Directory.ensure_directory_accessible(dir_path):
                    return dir_path
                
            except Exception:
                return None
        else:
            return default_path

    @staticmethod
    def open_directory_in_explorer(directory: str):
        if sys.platform == "win32":
            os.startfile(directory)

        elif sys.platform == "linux":
            subprocess.Popen(["xdg-open", directory])

        elif sys.platform == "darwin":
            subprocess.Popen(["open", directory])

    @staticmethod
    def open_files_in_explorer(directory: str, files: list[str]):
        if sys.platform == "win32":
            Directory.msw_SHOpenFolderAndSelectItems(directory, files)

        elif sys.platform == "linux":
            subprocess.Popen(["xdg-open", directory])

        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", directory])

    @staticmethod
    def msw_SHOpenFolderAndSelectItems(directory: str, files: list[str]):
        class ITEMIDLIST(ctypes.Structure):
            _fields_ = [("mkid", ctypes.c_byte)]

        def get_pidl(path):
            pidl = ctypes.POINTER(ITEMIDLIST)()
            ctypes.windll.shell32.SHParseDisplayName(path, None, ctypes.byref(pidl), 0, None)
            return pidl

        # 拼接完整路径
        full_paths = [str(Path(directory, f)) for f in files]

        ctypes.windll.ole32.CoInitialize(None)
        try:
            folder_pidl = get_pidl(directory)

            pidl_array_type = ctypes.POINTER(ITEMIDLIST) * len(full_paths)

            pidl_array = pidl_array_type()

            for i, p in enumerate(full_paths):
                pidl_array[i] = get_pidl(p)

            ctypes.windll.shell32.SHOpenFolderAndSelectItems(folder_pidl, len(full_paths), pidl_array, 0)
        finally:
            ctypes.windll.ole32.CoUninitialize()

