def message_box(message: str, caption: str):
    import platform

    if platform.platform().startswith("Windows"):
        from utils.module.messagebox import show_message

        show_message(caption, message)

try:
    import wx

except ImportError as e:
    message_box("缺少 Microsoft Visual C++ 运行库，无法运行本程序。\n\n请前往 https://aka.ms/vs/17/release/vc_redist.x64.exe 下载安装 Microsoft Visual C++ 2015-2022 运行库。", "Runtime Error")

    raise e

try:
    import os

    from utils.config import Config
    from utils.common.enums import Platform
    from utils.auth.cookie import CookieUtils

    from gui.window.main.main_v3 import MainWindow

except Exception as e:
    import traceback
    message_box(f"初始化程序失败\n\n{traceback.format_exc()}", "Fatal Error")

    raise e

class APP(wx.App):
    def __init__(self):
        self.init_env()

        wx.App.__init__(self)
        
        # 设置语言环境为中文
        self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
        self.SetAppName(Config.APP.name)

    def init_env(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                self.init_msw_env()

            case Platform.Linux:
                self.init_linux_env()

        self.init_vlc_env()

        CookieUtils.init_cookie_params()

    def init_msw_env(self):
        import ctypes
        import subprocess

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        subprocess.run("chcp 65001", stdout = subprocess.PIPE, shell = True)

    def init_linux_env(self):
        os.environ['GDK_BACKEND'] = "x11"

    def init_vlc_env(self):
        os.environ['PYTHON_VLC_MODULE_PATH'] = "./vlc"

if __name__ == "__main__":
    app = APP()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()
