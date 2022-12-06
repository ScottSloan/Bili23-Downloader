import wx
import wx.adv

from utils.config import Config
from utils.api import API

class AboutWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent)

        info = wx.adv.AboutDialogInfo()
        info.Name = Config.app_name
        info.Version = Config.app_version
        info.Copyright = "Copyright (C) 2022 Scott Sloan"
        info.Developers = ["Scott Sloan"]
        info.Licence = "MIT License"

        info.SetWebSite(API.App.website_api(), "项目主页")
        info.Description = "\nBili23 Downloader GUI 桌面端版本\n\n下载 Bilibili 视频/番剧/电影/纪录片 等资源\n\n发布日期：{}\n".format(Config.app_date)
        
        info.Icon = wx.Icon(Config.res_icon)

        wx.adv.AboutBox(info)