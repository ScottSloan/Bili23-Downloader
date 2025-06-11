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
                subprocess.Popen(f'xdg-open "{Config.Download.path}"', shell = True)

            case Platform.macOS:
                subprocess.Popen(f'open -R "{path}"', shell = True)

    @classmethod
    def get_file_ext_associated_app(cls, file_ext: str):
        def _linux():
            _desktop = subprocess.Popen("xdg-mime query default video/mp4", stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True)

            _desktop_path = os.path.join("/usr/share/applications", _desktop.stdout.read().replace("\n", ""))

            _exec = subprocess.Popen(f"grep '^Exec=' {_desktop_path} | head -n 1 | cut -d'=' -f2", stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True)

            return _exec.stdout.read().replace("\n", "")

        match Platform(Config.Sys.platform):
            case Platform.Windows:
                result, buffer = cls._msw_AssocQueryStringW(file_ext)

                if result == 0:
                    return (True, str(buffer.value))
                else:
                    return (False, "")

            case Platform.Linux:
                return (True, _linux())

            case Platform.macOS:
                # macOS 不支持获取默认程序
                return (False, "")

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

    @staticmethod
    def _msw_AssocQueryStringW(file_ext: str):
        from ctypes import wintypes

        buffer = ctypes.create_unicode_buffer(512)
        pcchOut = wintypes.DWORD(512)
        
        result = ctypes.windll.shlwapi.AssocQueryStringW(0x00000000, 1, file_ext, None, buffer, ctypes.byref(pcchOut))

        return (result, buffer)