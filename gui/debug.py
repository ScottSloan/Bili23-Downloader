import wx
import wx.dataview

from .templates import Frame

from utils.bangumi import BangumiInfo
from utils.tools import *
from utils.api import API

class DebugWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "Debug")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_video_info()

    def init_UI(self):
        info_box = wx.StaticBox(self.panel, -1, "视频信息")

        self.info_list = wx.dataview.DataViewListCtrl(self.panel, -1, size = self.FromDIP((500, 220)))

        self.refresh_btn = wx.Button(self.panel, -1, "刷新", size = self.FromDIP((90, 30)))

        self.info_sbox = wx.StaticBoxSizer(info_box, wx.VERTICAL)

        self.info_sbox.Add(self.info_list, 1, wx.ALL | wx.EXPAND, 10)
        self.info_sbox.Add(self.refresh_btn, 0, wx.ALL & ~(wx.TOP), 10)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.info_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

        self.init_menu()

    def Bind_EVT(self):
        self.info_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.show_menu_EVT)

        self.refresh_btn.Bind(wx.EVT_BUTTON, self.refresh_btn_EVT)

    def init_menu(self):
        self.menu = wx.Menu()

        self.copy_title_id = wx.NewIdRef()
        self.menu.Append(self.copy_title_id, "复制视频标题")

        self.copy_cover_id = wx.NewIdRef()
        self.menu.Append(self.copy_cover_id, "复制视频封面链接")
        
        self.menu.AppendSeparator()
        
        self.copy_bvid_id = wx.NewIdRef()
        self.menu.Append(self.copy_bvid_id, "复制 bvid")
        
        self.copy_avid_id = wx.NewIdRef()
        self.menu.Append(self.copy_avid_id, "复制 avid")

        self.copy_epid_id = wx.NewIdRef()
        self.menu.Append(self.copy_epid_id, "复制 epid")

        self.copy_cid_id = wx.NewIdRef()
        self.menu.Append(self.copy_cid_id, "复制 cid")
        
        self.menu.AppendSeparator()

        self.copy_url_bvid_id = wx.NewIdRef()
        self.menu.Append(self.copy_url_bvid_id, "复制视频链接 (bvid)")

        self.copy_url_epid_id = wx.NewIdRef()
        self.menu.Append(self.copy_url_epid_id, "复制视频链接 (epid)")
         
        self.copy_short_link_id = wx.NewIdRef()
        self.menu.Append(self.copy_short_link_id, "复制视频短链接 (b23.tv)")

        self.menu.AppendSeparator()

        self.copy_durl_api_id = wx.NewIdRef()
        self.menu.Append(self.copy_durl_api_id, "复制下载链接 (api)")
        
        self.init_menu_EVT()

    def init_menu_EVT(self):
        self.Bind(wx.EVT_MENU, self.copy_title_EVT, id = self.copy_title_id)
        
        self.Bind(wx.EVT_MENU, self.copy_bvid_EVT, id = self.copy_bvid_id)
        self.Bind(wx.EVT_MENU, self.copy_avid_EVT, id = self.copy_avid_id)
        self.Bind(wx.EVT_MENU, self.copy_epid_EVT, id = self.copy_epid_id)
        self.Bind(wx.EVT_MENU, self.copy_cid_EVT, id = self.copy_cid_id)
        
        self.Bind(wx.EVT_MENU, self.copy_url_bvid_EVT, id = self.copy_url_bvid_id)
        self.Bind(wx.EVT_MENU, self.copy_url_epid_EVT, id = self.copy_url_epid_id)
        self.Bind(wx.EVT_MENU, self.copy_short_link_EVT, id = self.copy_short_link_id)

    def init_info_list(self):
        self.type = None if not hasattr(self.Parent, "type") else self.Parent.type

        self.info_list.AppendTextColumn("序号", width = self.FromDIP(40))
        self.info_list.AppendTextColumn("标题", width = self.FromDIP(250))
        self.info_list.AppendTextColumn("bvid", width = self.FromDIP(125))
        self.info_list.AppendTextColumn("avid", width = self.FromDIP(100))
        self.info_list.AppendTextColumn("epid", width = self.FromDIP(100))
        self.info_list.AppendTextColumn("cid", width = self.FromDIP(100))
        
        self.info_list.AppendTextColumn("封面", width = 0)

    def init_video_info(self):
        self.init_info_list()

        if self.type == None:
            return

        elif self.type == BangumiInfo:
            self.init_bangumi_info()
    
    def init_bangumi_info(self):
        index = 0

        for episodes_list in BangumiInfo.sections.values():
            for index, episode in enumerate(episodes_list):

                index_s = str(index + 1)
                title = format_bangumi_title(episode)
                bvid = episode["bvid"]
                aid = str(episode["aid"])
                epid = str(episode["id"])
                cid = str(episode["cid"])

                cover = str(episode["cover"])
                link = str(episode["short_link"])

                item = [index_s, title, bvid, aid, epid, cid, cover, link]
                
                self.info_list.AppendItem(item)
                
                index += 1

    def show_menu_EVT(self, event):
        self.index = self.info_list.GetSelectedRow()

        self.PopupMenu(self.menu)

    def refresh_btn_EVT(self, event):
        self.init_video_info()

        self.panel.Layout()
    
    def copy_title_EVT(self, event):
        title = self.info_list.GetTextValue(self.index, 1)

        copy_text(title)
    
    def copy_cover_EVT(self, event):
        cover = self.info_list.GetTextValue(self.index, 6)

        copy_text(cover)

    def copy_bvid_EVT(self, event):
        bvid = self.info_list.GetTextValue(self.index, 2)

        copy_text(bvid)
    
    def copy_avid_EVT(self, event):
        avid = self.info_list.GetTextValue(self.index, 3)

        copy_text(avid)

    def copy_epid_EVT(self, event):
        epid = self.info_list.GetTextValue(self.index, 4)

        copy_text(epid)

    def copy_cid_EVT(self, event):
        cid = self.info_list.GetTextValue(self.index, 5)

        copy_text(cid)

    def copy_url_bvid_EVT(self, event):
        bvid = self.info_list.GetTextValue(self.index, 2)

        copy_text(API.URL.get_url_bvid(bvid))
    
    def copy_url_epid_EVT(self, event):
        epid = self.info_list.GetTextValue(self.index, 4)

        copy_text(API.URL.get_url_epid(epid))
    
    def copy_short_link_EVT(self, event):
        link = self.info_list.GetTextValue(self.index, 7)

        copy_text(link)