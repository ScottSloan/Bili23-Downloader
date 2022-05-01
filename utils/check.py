import wx
import os
import json
import requests
import datetime

from utils.tools import get_header, get_proxy
from utils.config import Config

class CheckUtils:
    def CheckUpdate() -> list:
        url = "https://auth.hanloth.cn/?type=update&pid=39&token=Mjp81YXdxcUk95ad"

        try:
            req = requests.get(url, headers = get_header(), proxies = get_proxy(), timeout = 2)
        except:
            return None

        req_json = json.loads(req.text)

        name  = req_json["name"]
        description = req_json["description"]
        version = req_json["version"]

        new = True if Config.VERSION_CODE < version else False
        return [new, name, description, version]
    
    def CheckFFmpeg():
        if not os.path.exists(Config.ffmpeg_path):
            dialog = wx.MessageDialog(None, "未安装 FFmpeg\n\n尚未安装 FFmpeg，可能无法正常下载视频，请问是否安装 FFmpeg？", "提示",  style = wx.ICON_INFORMATION | wx.YES_NO)
            dialog.SetYesNoLabels("安装", "取消")

            if dialog.ShowModal() == wx.ID_YES:
                import webbrowser
                webbrowser.open("https://ffmpeg.org/download.html")

                wx.MessageDialog(None, "下载后，请将 ffmpeg.exe 放置到程序运行目录下", "提示",  style = wx.ICON_INFORMATION).ShowModal()

    def CheckLogin():
        if Config.user_expire == "": return
        
        expire = datetime.datetime.strptime(Config.user_expire, "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()

        isoutdated = (expire - now) <= datetime.timedelta(hours = 0)

        if isoutdated:
            wx.MessageDialog(None, "登录过期\n\n登录过期，请重新登录", "提示", wx.ICON_WARNING).ShowModal()

    def ShowMessageUpdate(parent, info: list):
        dialog = wx.MessageDialog(parent, "有新的更新可用\n\n{0}\n\n更新说明：{1}".format(info[1], info[2], info[3]), "提示", wx.ICON_INFORMATION | wx.YES_NO)
        dialog.SetYesNoLabels("马上更新", "稍后更新")

        if dialog.ShowModal() == wx.ID_YES:
            import webbrowser
            webbrowser.open(Config.WEBSITE)

app = wx.App()

CheckUtils.CheckFFmpeg()
CheckUtils.CheckLogin()