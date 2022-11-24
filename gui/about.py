import wx
import wx.adv

from utils.config import Config

class AboutWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent)

        info = wx.adv.AboutDialogInfo()
        info.Name = "Bili23 Downloader"
        info.Version = Config.app_version
        info.Copyright = "Copyright (C) 2022 Scott Sloan"
        info.Developers = ["Scott Sloan"]
        info.Licence = "MIT License"

        info.SetWebSite(Config.app_website, "Github")

        info.Description = "下载 Bilibili 视频/番剧/电影/纪录片 等资源\n\n发布日期：{}\n".format(Config.app_date)
        info.Icon = wx.Icon(Config.res_icon)

        wx.adv.AboutBox(info)