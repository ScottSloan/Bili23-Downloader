import os
import ctypes
import subprocess

from utils.config import Config

from utils.common.enums import Platform

class DirectoryUtils:
    @staticmethod
    def open_directory(directory: str):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                os.startfile(directory)

            case Platform.Linux:
                subprocess.Popen(f'xdg-open "{directory}"', shell = True)

            case Platform.macOS:
                subprocess.Popen(f'open "{directory}"', shell = True)

    @classmethod
    def open_file_location(cls, path: str):
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