import wx
import wx.adv

class NotificationManager:
    def __init__(self, parent):
        self.parent = parent

        self.notification = wx.adv.NotificationMessage()

    def show_toast(self, title: str, message: str, flags: int):
        self.notification.SetTitle(title)
        self.notification.SetMessage(message)
        self.notification.SetFlags(flags)

        self.notification.Show()
    