import wx

from utils.config import Config

from utils.common.enums import Platform

from gui.component.window.frame import Frame

class DownloadManagerWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "下载管理")

        self.set_window_params()

        self.init_UI()

    def init_UI(self):
        pass

    def set_window_params(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                if self.GetDPIScaleFactor() >= 1.5:
                    size = self.FromDIP((930, 550))
                else:
                    size = self.FromDIP((960, 580))
            
            case Platform.macOS:
                size = self.FromDIP((1000, 600))
            
            case Platform.Linux:
                size = self.FromDIP((1070, 650))

        self.SetSize(size)