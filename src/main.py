import os
import platform

def message_box(message: str, caption: str):
    if platform.platform().startswith("Windows"):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, caption, 0x0 | 0x30)
    else:
        wx.LogError(message)

def get_traceback():
    import traceback

    return traceback.format_exc()

try:
    import wx

except ImportError as e:
    if platform.platform().startswith("Windows"):
        message_box(f"缺少 Microsoft Visual C++ 运行库，无法运行本程序。\n\n请前往 https://aka.ms/vs/17/release/vc_redist.x64.exe 下载安装 Microsoft Visual C++ 2015-2022 运行库。\n\n{get_traceback()}", "Runtime Error")

    raise e

import google.protobuf

protobuf_version = google.protobuf.__version__

if not protobuf_version.startswith("6"):
    msg = f"请更新 protobuf 至最新版本\n当前版本：{protobuf_version}\n建议版本：6.32.0 或更高"
    message_box(f"{msg}\n\n执行：pip install protobuf --upgrade", "Fatal Error")

    raise ImportError(msg)

try:
    from utils.config import Config
    from utils.common.enums import Platform
    from utils.auth.cookie import Cookie

    from gui.window.main.main_v3 import MainWindow

    Cookie.init_cookie_params()

except Exception as e:
    message_box(f"初始化程序失败\n\n{get_traceback()}", "Fatal Error")

    raise e

class APP(wx.App):
    def __init__(self):
        self.init_env()

        wx.App.__init__(self)
        
        # 设置语言环境为中文
        self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
        self.SetAppName(Config.APP.name)

        main_window = MainWindow(None)
        main_window.Show()

    def init_env(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                self.init_msw_env()

            case Platform.Linux:
                self.init_linux_env()

        self.init_vlc_env()

    def init_msw_env(self):
        if not os.environ.get("PYSTAND"):
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)

        import subprocess
        subprocess.run("chcp 65001", stdout = subprocess.PIPE, shell = True)

    def init_linux_env(self):
        os.environ['GDK_BACKEND'] = "x11"
        #os.environ['GDK_DPI_SCALE'] = "1.25"

    def init_vlc_env(self):
        os.environ['PYTHON_VLC_MODULE_PATH'] = "./vlc"

if __name__ == "__main__":
    app = APP()
    app.MainLoop()
    