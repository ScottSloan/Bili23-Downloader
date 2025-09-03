import wx
import os
import wx.adv

from utils.config import Config

class NotificationManager:
    def __init__(self, parent):
        self.parent = parent

        self.notification = wx.adv.NotificationMessage()
        self.notification.MSWUseToasts(os.environ.get("PYSTAND"), appId = Config.APP.id)

    def show_toast(self, title: str, message: str, flags: int):
        self.notification.SetTitle(title)
        self.notification.SetMessage(message)
        self.notification.SetFlags(flags)

        self.notification.Show()
    