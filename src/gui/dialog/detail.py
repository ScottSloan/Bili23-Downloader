import wx
import io
import wx.html

from utils.config import Config
from utils.tool_v2 import RequestTool
from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo

class DetailDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "详细信息")

        self.init_UI()

        self.CenterOnParent()
        
    def init_UI(self):
        self.note = wx.Simplebook(self, -1)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 1, wx.EXPAND)

        self.SetSizer(vbox)
    
    def set_video_page(self):
        self.note.AddPage(VideoPage(self.note), "video")

        self.fit_window()

    def set_bangumi_page(self):
        self.note.AddPage(BangumiPage(self.note), "bangumi")

        self.fit_window()

    def fit_window(self):
        self.Fit()

        self.CenterOnParent()

class DetailPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.html_page = wx.html.HtmlWindow(self, -1, size = self.FromDIP((550, 300)))

        self.ID_COPY = wx.NewIdRef()

        self.html_page.Bind(wx.EVT_RIGHT_DOWN, self.onContextMenu)

        self.Bind(wx.EVT_MENU, self.onCopy, id = self.ID_COPY)

    def onContextMenu(self, event):
        def get_menu():
            menu = wx.Menu()

            copy_menuitem = wx.MenuItem(menu, self.ID_COPY, "复制所选内容(C)")

            menu.Append(copy_menuitem)

            return menu

        self.html_page.PopupMenu(get_menu())

    def onCopy(self, event):
        text = self.html_page.SelectionToText()

        if text:
            wx.TheClipboard.SetData(wx.TextDataObject(text))

class VideoPage(DetailPage):
    def __init__(self, parent):
        DetailPage.__init__(self, parent)

        self.init_UI()
    
    def init_UI(self):
        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")

        _set_dark_mode()

        font: wx.Font = self.GetFont()

        title_div = f"""<font size="5" face="{font.GetFaceName()}">{VideoInfo.title}</font>"""
        views_div = f"""<div id="views"><span style="font-family: {font.GetFaceName()}; color: rgba(97, 102, 109, 1);">{VideoInfo.views}播放&nbsp&nbsp {VideoInfo.danmakus}弹幕&nbsp&nbsp {VideoInfo.pubtime}</span></div>"""
        desc_div = f"""<div id="desc"><span style="font-family: {font.GetFaceName()};">{VideoInfo.desc}</span></div>"""
        tag_span = [f"""<span style="font-family: {font.GetFaceName()}; background-color: rgba(241, 242, 243, 1); color: rgba(97, 102, 109, 1);">{i}</span><span>&nbsp&nbsp</span>""" for i in VideoInfo.tag_list]
        tag_div = """<div id="tag">{}</div>""".format("".join(tag_span))

        body = "<br>".join([title_div, views_div, desc_div, tag_div])

        self.html_page.SetPage(f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>{body}</body></html>""")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(15)
        vbox.Add(self.html_page, 1, wx.ALL | wx.EXPAND, 10)
        vbox.AddSpacer(15)

        self.SetSizerAndFit(vbox)

class BangumiPage(DetailPage):
    def __init__(self, parent):
        DetailPage.__init__(self, parent)

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

        cover_bmp = wx.StaticBitmap(self, -1, get_cover().ConvertToBitmap())

        title_div = f"""<font size="5" face="{font.GetFaceName()}">{BangumiInfo.title}</font>"""
        views_div = f"""<div id="views"><span style="color: rgba(97, 102, 109, 1); font-family: {font.GetFaceName()};">{BangumiInfo.views}播放&nbsp&nbsp·&nbsp {BangumiInfo.danmakus}弹幕&nbsp&nbsp·&nbsp {BangumiInfo.followers}</span></div>"""
        tag_div = f"""<div id="tag"><span style="color: rgba(97, 102, 109, 1); font-family: {font.GetFaceName()};">{BangumiInfo.styles}&nbsp&nbsp·&nbsp&nbsp{BangumiInfo.new_ep}&nbsp&nbsp·&nbsp {BangumiInfo.bvid}</span></div>"""
        actors_div = f"""<div id="actors"><span style="color: rgba(97, 102, 109, 1); font-family: {font.GetFaceName()}">演员：{BangumiInfo.actors}</span></div>"""
        desc_div = f"""<div id="desc"><span style="font-family: {font.GetFaceName()}">简介：{BangumiInfo.evaluate}</span></div>"""

        body = "<br>".join([title_div, views_div, tag_div, actors_div, desc_div])

        self.html_page.SetPage(f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>{body}</body></html>""")

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(self.html_page, 1, wx.ALL | wx.EXPAND, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(15)
        hbox.Add(cover_bmp, 0, wx.ALL, 10)
        hbox.Add(right_vbox, 1, wx.EXPAND)
        hbox.AddSpacer(15)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(15)
        vbox.Add(hbox, 1, wx.EXPAND)
        vbox.AddSpacer(15)

        self.SetSizerAndFit(vbox)