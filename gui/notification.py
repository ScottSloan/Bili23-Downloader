import wx
import wx.adv

from utils.config import Config
class Notification:
    def show_dialog(parent, code: int):
        if code == 200:
            wx.MessageDialog(parent, "检查更新失败\n\n当前无法检查更新，请稍候再试", "警告", wx.ICON_WARNING).ShowModal()

        if code == 201:
            wx.MessageDialog(parent, "当前没有可用更新", "提示", wx.ICON_INFORMATION).ShowModal()

        if code == 203:
            wx.MessageDialog(parent, "使用帮助\n\nhelp", "使用帮助", wx.ICON_INFORMATION).ShowModal()
        
        if code == 204:
            wx.MessageDialog(parent, "未指定播放器路径\n\n尚未指定播放器路径，请添加路径后再试", "警告", wx.ICON_WARNING).ShowModal()
        
    def show_notification_download_finish():
        msg = wx.adv.NotificationMessage("下载完成", "所有任务已下载完成", flags = wx.ICON_INFORMATION)

        if Config.PLATFORM.startswith("Windows"):
            msg.MSWUseToasts()

        msg.Show(timeout = 5)
        msg.Close()

    def show_notification_download_error():
        msg = wx.adv.NotificationMessage("下载失败", '视频下载失败', flags = wx.ICON_ERROR)

        if Config.PLATFORM.startswith("Windows"):
            msg.MSWUseToasts()

        msg.Show(timeout = 5)
        msg.Close()