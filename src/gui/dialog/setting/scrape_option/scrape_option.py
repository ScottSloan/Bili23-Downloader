import wx
import gettext

from utils.config import Config
from utils.common.enums import Platform

from gui.dialog.setting.scrape_option.video import VideoPage
from gui.dialog.setting.scrape_option.episode import EpisodePage
from gui.dialog.setting.scrape_option.movie import MoviePage
from gui.dialog.setting.scrape_option.lesson import LessonPage

from gui.component.window.dialog import Dialog

_ = gettext.gettext

class ScrapeOptionDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, _("刮削设置"))

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        self.tree_book = wx.Treebook(self, -1, size = self.get_book_size())

        self.tree_book.AddPage(wx.Panel(self.tree_book), _("刮削设置          "))
        self.tree_book.AddSubPage(VideoPage(self.tree_book), _("投稿视频"))
        self.tree_book.AddSubPage(EpisodePage(self.tree_book), _("剧集"))
        self.tree_book.AddSubPage(MoviePage(self.tree_book), _("电影"))
        self.tree_book.AddSubPage(LessonPage(self.tree_book), _("课程"))
        self.tree_book.ExpandNode(0, True)
        self.tree_book.SetSelection(1)

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.tree_book, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def onOKEVT(self):
        scrape_option = {}

        for index in range(1, self.tree_book.GetPageCount()):
            page = self.tree_book.GetPage(index)

            scrape_option.update(page.save())

        Config.Temp.scrape_option = scrape_option

    def get_book_size(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                if Config.Basic.language == "zh_CN":
                    return self.FromDIP((400, 200))
                else:
                    return self.FromDIP((500, 200))
            
            case Platform.Linux | Platform.macOS:
                if Config.Basic.language == "zh_CN":
                    return self.FromDIP((500, 280))
                else:
                    return self.FromDIP((600, 280))
