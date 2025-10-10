import os
import sys
import platform

def message_box(message: str, caption: str, wx_status: bool = True, e = None):
    if platform.platform().startswith("Windows"):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, caption, 0x0 | 0x30)
    else:
        if wx_status:
            wx.LogError(message)
        else:
            raise e
        
    sys.exit()

def get_traceback():
    import traceback

    return traceback.format_exc()

try:
    import wx

except ImportError as e:
    message_box(f"缺少 Microsoft Visual C++ 运行库，无法运行本程序。\n\n请前往 https://aka.ms/vs/17/release/vc_redist.x64.exe 下载安装 Microsoft Visual C++ 2015-2022 运行库。\n\n{get_traceback()}", "Runtime Error", False, e)

except Exception as e:
    message_box(f"初始化 wxPython 失败\n\n{get_traceback()}", "Fatal Error", False, e)

try:
    import google.protobuf

    if (protobuf_version := google.protobuf.__version__) and not protobuf_version.startswith("6"):
        msg = f"请更新 protobuf 至最新版本\n当前版本：{protobuf_version}\n建议版本：6.32.0 或更高"
        message_box(f"{msg}\n\n执行：pip install protobuf --upgrade", "Fatal Error")

        raise ImportError(msg)
    
except Exception as e:
    message_box(f"初始化 protobuf 失败\n\n{get_traceback()}", "Fatal Error", False, e)

try:
    from utils.config import Config
    from utils.common.enums import Platform
    from utils.auth.cookie import Cookie

    from gui.window.main.main_v3 import MainWindow

    Cookie.init_cookie_params()

except Exception as e:
    message_box(f"初始化程序失败\n\n{get_traceback()}", "Fatal Error")

class APP(wx.App):
    def __init__(self):
        self.init_env()

        wx.App.__init__(self)

        self.init_lang()

        self.SetAppName(Config.APP.name)

        main_window = MainWindow(None)
        main_window.Show()

    def init_env(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                self.init_msw_env()

            case Platform.Linux:
                self.init_linux_env()

            case Platform.macOS:
                self.init_macos_env()

        self.init_vlc_env()

    def init_msw_env(self):
        import ctypes
        import subprocess

        if not os.environ.get("PYSTAND"):
            ctypes.windll.shcore.SetProcessDpiAwareness(2)

        ctypes.windll.kernel32.CreateMutexW(None, False, Config.APP.id)

        if ctypes.windll.kernel32.GetLastError() == 183:
            message_box("Bili23 Downloader 已在运行！", "警告")
            sys.exit()
        
        subprocess.run("chcp 65001", stdout = subprocess.PIPE, shell = True)

    def init_linux_env(self):
        self.lock_file()
        
        os.environ['GDK_BACKEND'] = "x11"
        #os.environ['GDK_DPI_SCALE'] = "1.25"

    def init_macos_env(self):
        self.lock_file()

    def init_vlc_env(self):
        os.environ['PYTHON_VLC_MODULE_PATH'] = "./vlc"

    def init_lang(self):
        import gettext

        if Config.Basic.language == "zh_CN":
            self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)

        else:
            self.locale = wx.Locale(wx.LANGUAGE_ENGLISH_US)
        
        os.environ["LANGUAGE"] = Config.Basic.language

        gettext.bindtextdomain("lang", self.locale_dir)
        gettext.textdomain("lang")

    def lock_file(self):
        import fcntl

        LOCK_FILE = os.path.join(os.getcwd(), "app.lock")

        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)

        except Exception as e:
            wx.LogError("无法创建锁文件")
            sys.exit()

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        except IOError:
            os.close(fd)
            wx.LogError("Bili23 Downloader 已在运行！")
            sys.exit()

    @property
    def locale_dir(self):
        import importlib.resources

        with importlib.resources.path("Locale", "0") as file_path:
            return os.path.dirname(file_path)

if __name__ == "__main__":
    app = APP()
    app.MainLoop()