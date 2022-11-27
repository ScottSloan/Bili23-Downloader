import wx
import wx.adv

from utils.config import Config

class Notification:
    def show_notification_download_finish():
        msg = wx.adv.NotificationMessage("下载完成", "所有任务已下载完成", flags = wx.ICON_INFORMATION)

        if Config.platform.startswith("Windows"):
            msg.MSWUseToasts()

        msg.Show(timeout = 5)
        msg.Close()

    def show_notification_download_error():
        msg = wx.adv.NotificationMessage("下载失败", '任务下载失败', flags = wx.ICON_ERROR)

        if Config.platform.startswith("Windows"):
            msg.MSWUseToasts()

        msg.Show(timeout = 5)
        msg.Close()