import wx
import io

from utils.config import Config
from utils.tool_v2 import RequestTool
from utils.parse.bangumi import BangumiInfo

class DetailDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "详细信息")

        self.init_UI()

        self.CenterOnParent()
        
    def init_UI(self):
        self.note = wx.Simplebook(self, -1)

        self.note.AddPage(BangumiPage(self.note), "bangumi")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

class VideoPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()
    
    def init_UI(self):
        pass

class BangumiPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()
    
    def init_UI(self):
        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")

        def get_cover():
            contents = RequestTool.request(BangumiInfo.cover)

            temp_image = wx.Image(io.BytesIO(contents))

            return temp_image.Scale(self.FromDIP(165), self.FromDIP(221), wx.IMAGE_QUALITY_HIGH)

        _set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 3)

        self.cover_bmp = wx.StaticBitmap(self, -1, get_cover().ConvertToBitmap())

        self.title_lab = wx.StaticText(self, -1, BangumiInfo.title)
        self.title_lab.SetFont(font)

        views_lab = wx.StaticText(self, -1, f"{BangumiInfo.views}播放")
        views_lab.SetForegroundColour(wx.Colour(97, 102, 109))
        danmakus_lab = wx.StaticText(self, -1, f"{BangumiInfo.danmakus}弹幕")
        danmakus_lab.SetForegroundColour(wx.Colour(97, 102, 109))
        followers_lab = wx.StaticText(self, -1, BangumiInfo.followers)
        followers_lab.SetForegroundColour(wx.Colour(97, 102, 109))

        view_hbox = wx.BoxSizer(wx.HORIZONTAL)
        view_hbox.Add(views_lab, 0, wx.ALL, 10)
        view_hbox.Add(danmakus_lab, 0, wx.ALL, 10)
        view_hbox.Add(followers_lab, 0, wx.ALL, 10)

        tag_lab = wx.StaticText(self, -1, BangumiInfo.styles)
        tag_lab.SetForegroundColour(wx.Colour(97, 102, 109))
        year_lab = wx.StaticText(self, -1, "2023")
        year_lab.SetForegroundColour(wx.Colour(97, 102, 109))
        new_ep_lab = wx.StaticText(self, -1, BangumiInfo.new_ep)
        new_ep_lab.SetForegroundColour(wx.Colour(97, 102, 109))
        bvid_lab = wx.StaticText(self, -1, BangumiInfo.bvid)
        bvid_lab.SetForegroundColour(wx.Colour(97, 102, 109))

        tag_hbox = wx.BoxSizer(wx.HORIZONTAL)
        tag_hbox.Add(tag_lab, 0, wx.ALL, 10)
        tag_hbox.Add(year_lab, 0, wx.ALL, 10)
        tag_hbox.Add(new_ep_lab, 0, wx.ALL, 10)
        tag_hbox.Add(bvid_lab, 0, wx.ALL, 10)

        actors_lab = wx.StaticText(self, -1, f"声优：{BangumiInfo.actors}")
        actors_lab.SetForegroundColour(wx.Colour(97, 102, 109))

        desc_lab = wx.StaticText(self, -1, f"简介：{BangumiInfo.evaluate}")

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(self.title_lab, 0, wx.ALL, 10)
        right_vbox.Add(view_hbox, 0, wx.EXPAND)
        right_vbox.Add(tag_hbox, 0, wx.EXPAND)
        right_vbox.Add(actors_lab, 0, wx.ALL, 10)
        right_vbox.Add(desc_lab, 0, wx.ALL & (~wx.TOP), 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(15)
        hbox.Add(self.cover_bmp, 0, wx.ALL, 10)
        hbox.Add(right_vbox, 0, wx.EXPAND)
        hbox.AddSpacer(15)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(15)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddSpacer(15)

        self.SetSizerAndFit(vbox)