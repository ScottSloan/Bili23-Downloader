import wx
import wx.adv

from utils.config import Config

class AboutWindow(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        info = wx.adv.AboutDialogInfo()
        info.Name = "Bili23 Downloader"
        info.Version = Config._version
        info.Copyright = "Copyright (C) 2022 Scott Sloan"
        info.Developers = ["Scott Sloan"]
        info.SetWebSite(Config._website, "项目地址")

        info.Description = "下载 Bilibili 视频/番剧/电影/纪录片 等资源\n\n发布日期：{}\n\n本程序仅供学习交流使用，请勿用于商业用途。".format(Config._date)
        info.Icon = wx.Icon(Config._logo)

        wx.adv.AboutBox(info)
        