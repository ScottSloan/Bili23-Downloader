import os
import ctypes
import subprocess
from typing import List

from utils.common.enums import Platform

class Directory:
    @classmethod
    def create_directories(cls, directory_list: List[str]):
        for directory in directory_list:
            cls.create_directory(directory)

    @staticmethod
    def create_directory(directory: str):
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def open_directory(directory: str):
        from utils.config import Config

        match Platform(Config.Sys.platform):
            case Platform.Windows:
                os.startfile(directory)

            case Platform.Linux:
                subprocess.Popen(f'xdg-open "{directory}"', shell = True)

            case Platform.macOS:
                subprocess.Popen(f'open "{directory}"', shell = True)

    @classmethod
    def open_file_location(cls, path: str):
        from utils.config import Config
        
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                cls._msw_SHOpenFolderAndSelectItems(path)

            case Platform.Linux:
                subprocess.Popen(f'xdg-open "{os.path.dirname(path)}"', shell = True)

            case Platform.macOS:
                subprocess.Popen(f'open -R "{path}"', shell = True)

    @staticmethod
    def _msw_SHOpenFolderAndSelectItems(path: str):
        def get_pidl(path):
            pidl = ctypes.POINTER(ITEMIDLIST)()
            ctypes.windll.shell32.SHParseDisplayName(path, None, ctypes.byref(pidl), 0, None)
            
            return pidl
        
        class ITEMIDLIST(ctypes.Structure):
            _fields_ = [("mkid", ctypes.c_byte)]

        ctypes.windll.ole32.CoInitialize(None)

        try:
            folder_pidl = get_pidl(os.path.dirname(path))
            file_pidl = get_pidl(path)
            
            ctypes.windll.shell32.SHOpenFolderAndSelectItems(folder_pidl, 1, ctypes.byref(file_pidl), 0)

        finally:
            ctypes.windll.ole32.CoUninitialize()