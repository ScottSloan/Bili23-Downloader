import wx
import io
import wx.html

from utils.config import Config
from utils.tool_v2 import UniversalTool

from utils.common.enums import ParseType
from utils.common.thread import Thread
from utils.common.request import RequestUtils

from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.cheese import CheeseInfo

from gui.component.dialog import Dialog
from gui.component.panel import Panel

class DetailDialog(Dialog):
    def __init__(self, parent, parse_type: ParseType):
        self.parse_type = parse_type

        Dialog.__init__(self, parent, "详细信息")

        self.init_UI()

        self.set_page()
        
    def init_UI(self):
        self.set_dark_mode()

        self.note = wx.Simplebook(self, -1)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 1, wx.EXPAND)

        self.SetSizer(vbox)
    
    def set_page(self):
        match self.parse_type:
            case ParseType.Video:
                page = VideoPage(self.note)
            
            case ParseType.Bangumi:
                page = BangumiPage(self.note)

            case ParseType.Cheese:
                page = CheesePage(self.note)

        self.note.AddPage(page, "page")

        self.Fit()

        self.CenterOnParent()

class DetailPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.html_page = wx.html.HtmlWindow(self, -1, size = self.FromDIP((550, 300)))

        self.ID_COPY = wx.NewIdRef()

        self.html_page.Bind(wx.EVT_RIGHT_DOWN, self.onContextMenu)

        self.Bind(wx.EVT_MENU, self.onCopy, id = self.ID_COPY)

    def onContextMenu(self, event):
        def get_menu():
            menu = wx.Menu()

            copy_menuitem = wx.MenuItem(menu, self.ID_COPY, "复制所选内容(&C)")

            menu.Append(copy_menuitem)

            return menu

        self.html_page.PopupMenu(get_menu())

    def onCopy(self, event):
        text = self.html_page.SelectionToText()

        if text:
            wx.TheClipboard.SetData(wx.TextDataObject(text))

    def set_page(self, body: str):
        if Config.Sys.dark_mode:
            color: wx.Colour = self.GetParent().GetBackgroundColour()
        else:
            color = wx.Colour("white")
        
        self.html_page.SetPage(f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="background-color: rgba({color.GetRed()},{color.GetGreen()},{color.GetBlue()},1);">{body}</body></html>""")
    
    def get_text_color(self):
        if Config.Sys.dark_mode:
            return "rgba(255, 255, 255, 1)"
        else:
            return "rgba(0, 0, 0, 1)"
        
    def get_tag_background_color(self):
        if Config.Sys.dark_mode:
            return "rgba(55, 55, 55, 1)"
        else:
            return "rgba(241, 242, 243, 1)"
    
    def get_tag_color(self):
        if Config.Sys.dark_mode:
            return "rgba(255, 255, 255, 1)"
        else:
            return "rgba(97, 102, 109, 1)"
        
    def get_views_color(self):
        if Config.Sys.dark_mode:
            return "rgba(255, 255, 255, 1)"
        else:
            return "rgba(97, 102, 109, 1)"

class VideoPage(DetailPage):
    def __init__(self, parent):
        DetailPage.__init__(self, parent)

        self.init_UI()

        self.init_utils()
    
    def init_UI(self):
        font: wx.Font = self.GetFont()

        title_div = f"""<font size="5" face="{font.GetFaceName()}" style="color: {self.get_text_color()};">{VideoInfo.title}</font>"""
        views_div = f"""<div id="views"><span style="font-family: {font.GetFaceName()}; color: {self.get_views_color()};">{VideoInfo.views}播放&nbsp&nbsp {VideoInfo.danmakus}弹幕&nbsp&nbsp {UniversalTool.get_time_str_from_timestamp(VideoInfo.pubtime)}</span></div>"""
        desc_div = f"""<div id="desc"><span style="font-family: {font.GetFaceName()}; color: {self.get_text_color()};">{VideoInfo.desc}</span></div>"""

        body = "<br>".join([title_div, views_div, desc_div])

        self.set_page(body)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(10))
        vbox.Add(self.html_page, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.AddSpacer(self.FromDIP(10))

        self.SetSizerAndFit(vbox)
    
    def init_utils(self):
        def worker():
            def add_tag():
                font: wx.Font = self.GetFont()

                tag_span = [f"""<span style="font-family: {font.GetFaceName()}; background-color: {self.get_tag_background_color()}; color: {self.get_tag_color()};">{i}</span><span>&nbsp&nbsp</span>""" for i in VideoInfo.tag_list]
                tag_div = """<div id="tag">{}</div>""".format("".join(tag_span))

                self.html_page.AppendToPage(tag_div)

            self.GetParent().GetParent().GetParent().video_parser.get_video_tag()

            wx.CallAfter(add_tag)

        Thread(target = worker).start()

class BangumiPage(DetailPage):
    def __init__(self, parent):
        DetailPage.__init__(self, parent)

        self.init_UI()

        self.init_utils()
    
    def init_UI(self):
        def _img_load():
            font: wx.Font = self.GetFont()
            font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 5))

            bmp = wx.Bitmap(self.FromDIP(150), self.FromDIP(150))
            dc = wx.MemoryDC(bmp)

            dc.SetFont(font)

            text = "正在加载"
            width, height = dc.GetTextExtent(text)

            x = (self.FromDIP(150) - width) // 2
            y = (self.FromDIP(150) - height) // 2

            dc.Clear()
            dc.DrawText(text, x, y)

            return bmp

        font: wx.Font = self.GetFont()

        self.cover_bmp = wx.StaticBitmap(self, -1, _img_load(), size = self.FromDIP((165, 221)))

        title_div = f"""<font size="5" face="{font.GetFaceName()}" style="color: {self.get_text_color()};">{BangumiInfo.title}</font>"""
        views_div = f"""<div id="views"><span style="color: {self.get_views_color()}; font-family: {font.GetFaceName()};">{BangumiInfo.views}播放&nbsp&nbsp·&nbsp {BangumiInfo.danmakus}弹幕&nbsp&nbsp·&nbsp {BangumiInfo.followers}</span></div>"""
        tag_div = f"""<div id="tag"><span style="color: {self.get_views_color()}; font-family: {font.GetFaceName()};">{BangumiInfo.styles}&nbsp&nbsp·&nbsp&nbsp{BangumiInfo.new_ep}&nbsp&nbsp·&nbsp {BangumiInfo.bvid}</span></div>"""
        actors_div = f"""<div id="actors"><span style="color: {self.get_views_color()}; font-family: {font.GetFaceName()}">演员：{BangumiInfo.actors}</span></div>"""
        desc_div = f"""<div id="desc"><span style="font-family: {font.GetFaceName()}; color: {self.get_text_color()};">简介：{BangumiInfo.evaluate}</span></div>"""

        body = "<br>".join([title_div, views_div, tag_div, actors_div, desc_div])

        self.set_page(body)

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(self.html_page, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(self.FromDIP(10))
        hbox.Add(self.cover_bmp, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(right_vbox, 1, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(10))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(10))
        vbox.Add(hbox, 1, wx.EXPAND)
        vbox.AddSpacer(self.FromDIP(10))

        self.SetSizerAndFit(vbox)
    
    def init_utils(self):
        def worker():
            def set_bmp():
                temp_image = wx.Image(io.BytesIO(contents))

                bmp = temp_image.Scale(self.FromDIP(165), self.FromDIP(221), wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()
            
                self.cover_bmp.SetBitmap(bmp)

            contents = RequestUtils.request_get(BangumiInfo.cover).content

            wx.CallAfter(set_bmp)

        Thread(target = worker).start()

class CheesePage(DetailPage):
    def __init__(self, parent):
        DetailPage.__init__(self, parent)

        self.init_UI()
    
    def init_UI(self):
        font: wx.Font = self.GetFont()

        title_div = f"""<font size="5" face="{font.GetFaceName()}" style="color: {self.get_text_color()};">{CheeseInfo.title}</font>"""
        views_div = f"""<div id="views"><span style="font-family: {font.GetFaceName()}; color: {self.get_views_color()};">{CheeseInfo.views}播放&nbsp&nbsp {CheeseInfo.release}&nbsp&nbsp {CheeseInfo.expiry}</span></div>"""
        subtitle_div = f"""<div id="desc"><span style="font-family: {font.GetFaceName()}; color: {self.get_text_color()};">{CheeseInfo.subtitle}</span></div>"""

        body = "<br>".join([title_div, views_div, subtitle_div])

        self.set_page(body)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(10))
        vbox.Add(self.html_page, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.AddSpacer(self.FromDIP(10))

        self.SetSizerAndFit(vbox)