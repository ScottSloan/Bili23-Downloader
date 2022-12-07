import wx
import os
import wx.py
import requests
import wx.dataview

from .templates import Frame

from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.tools import *
from utils.api import API

class DebugWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "Debug")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_episodes_info()

    def init_UI(self):
        info_box = wx.StaticBox(self.panel, -1, "视频信息")

        self.info_list = wx.dataview.DataViewListCtrl(self.panel, -1, size = self.FromDIP((500, 220)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.refresh_btn = wx.Button(self.panel, -1, "刷新", size = self.FromDIP((90, 30)))
        self.info_json_btn = wx.Button(self.panel, -1, "保存视频信息 (json)", size = self.FromDIP((125, 30)))
        
        btn_hbox.Add(self.refresh_btn, 0, wx.ALL & (~wx.TOP), 10)
        btn_hbox.Add(self.info_json_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        self.info_sbox = wx.StaticBoxSizer(info_box, wx.VERTICAL)

        self.info_sbox.Add(self.info_list, 1, wx.ALL | wx.EXPAND, 10)
        self.info_sbox.Add(btn_hbox, 0, wx.EXPAND)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.info_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def Bind_EVT(self):
        self.info_list.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.show_menu_EVT)

        self.refresh_btn.Bind(wx.EVT_BUTTON, self.refresh_btn_EVT)
        self.info_json_btn.Bind(wx.EVT_BUTTON, self.info_json_btn_EVT)

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
        copy_epid_menu = wx.MenuItem(self.menu, self.copy_epid_id, "复制 epid")
        
        if self.type == VideoInfo:
            copy_epid_menu.Enable(False)

        self.menu.Append(copy_epid_menu)

        self.copy_cid_id = wx.NewIdRef()
        self.menu.Append(self.copy_cid_id, "复制 cid")
        
        self.menu.AppendSeparator()

        self.copy_url_bvid_id = wx.NewIdRef()
        self.menu.Append(self.copy_url_bvid_id, "复制视频链接 (bvid)")

        self.copy_url_epid_id = wx.NewIdRef()
        copy_url_epid_menu = wx.MenuItem(self.menu, self.copy_url_epid_id, "复制视频链接 (epid)")
        
        if self.type == VideoInfo:
            copy_url_epid_menu.Enable(False)

        self.menu.Append(copy_url_epid_menu)
         
        self.copy_short_link_id = wx.NewIdRef()
        self.menu.Append(self.copy_short_link_id, "复制视频短链接 (b23.tv)")

        self.menu.AppendSeparator()

        self.copy_durl_api_id = wx.NewIdRef()
        self.menu.Append(self.copy_durl_api_id, "复制下载链接 (api)")
        
        self.init_menu_EVT()

    def init_menu_EVT(self):
        self.Bind(wx.EVT_MENU, self.copy_title_EVT, id = self.copy_title_id)
        self.Bind(wx.EVT_MENU, self.copy_cover_EVT, id = self.copy_cover_id)
        
        self.Bind(wx.EVT_MENU, self.copy_bvid_EVT, id = self.copy_bvid_id)
        self.Bind(wx.EVT_MENU, self.copy_avid_EVT, id = self.copy_avid_id)
        self.Bind(wx.EVT_MENU, self.copy_epid_EVT, id = self.copy_epid_id)
        self.Bind(wx.EVT_MENU, self.copy_cid_EVT, id = self.copy_cid_id)
        
        self.Bind(wx.EVT_MENU, self.copy_url_bvid_EVT, id = self.copy_url_bvid_id)
        self.Bind(wx.EVT_MENU, self.copy_url_epid_EVT, id = self.copy_url_epid_id)
        self.Bind(wx.EVT_MENU, self.copy_short_link_EVT, id = self.copy_short_link_id)
        
        self.Bind(wx.EVT_MENU, self.copy_durl_api_EVT, id = self.copy_durl_api_id)

    def init_info_list(self):
        self.type = None if not hasattr(self.Parent, "type") else self.Parent.type
        
        self.info_list.ClearColumns()
        self.info_list.DeleteAllItems()

        self.info_list.AppendTextColumn("序号", width = self.FromDIP(40))
        self.info_list.AppendTextColumn("标题", width = self.FromDIP(250))
        self.info_list.AppendTextColumn("bvid", width = self.FromDIP(125))
        self.info_list.AppendTextColumn("avid", width = self.FromDIP(100))

        epid_col_width = 0 if self.type == VideoInfo else 100
        self.info_list.AppendTextColumn("epid", width = self.FromDIP(epid_col_width))
        self.info_list.AppendTextColumn("cid", width = self.FromDIP(100))
        
        self.info_list.AppendTextColumn("封面", width = 0)
        self.info_list.AppendTextColumn("link", width = 0)

    def init_episodes_info(self):
        self.init_info_list()

        if self.type == None:
            return
        
        if self.type == VideoInfo:
            self.init_video_info()

        elif self.type == BangumiInfo:
            self.init_bangumi_info()
    
    def init_video_info(self):
        if VideoInfo.type == "collection":
            index = 0

            for episodes_list in VideoInfo.sections.values():
                for episode in episodes_list:
                    index_s = str(index + 1)
                    title = episode["arc"]["title"]
                    bvid = episode["bvid"]
                    avid = str(episode["arc"]["aid"])
                    cid = str(episode["cid"])

                    cover = episode["arc"]["pic"]
                    link = API.URL.bvid_short_link_api(bvid)

                    item =[index_s, title, bvid, avid, "", cid, cover, link]

                    self.info_list.AppendItem(item)
                    
                    index += 1

        else:
            for index, episode in enumerate(VideoInfo.pages):
                index_s = str(index + 1)
                title = episode["part"]
                bvid = VideoInfo.bvid
                avid = str(VideoInfo.aid)
                cid = str(episode["cid"])

                if "first_frame" in episode:
                    cover = episode["first_frame"]
                else:
                    cover = VideoInfo.cover
                
                link = API.URL.bvid_short_link_api(VideoInfo.bvid)

                item =[index_s, title, bvid, avid, "", cid, cover, link]

                self.info_list.AppendItem(item) 

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

        self.init_menu()
        self.PopupMenu(self.menu)

    def refresh_btn_EVT(self, event):
        self.init_video_info()

        self.panel.Layout()

    def info_json_btn_EVT(self, event):
        if self.type == None:
            return

        wildcard = "JSON文件(*.json)|*.json"
        dlg = wx.FileDialog(self, "保存JSON文件", os.getcwd(), "info.json", wildcard = wildcard, style = wx.FD_SAVE)

        if dlg.ShowModal() == wx.ID_CANCEL:
            return

        if self.type == VideoInfo:
            url = API.Video.info_api(VideoInfo.bvid)
        else:
            url = API.Bangumi.info_api("ep_id", BangumiInfo.epid)

        info_request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        
        with open(dlg.GetPath(), "w", encoding = "utf-8") as f:
            f.write(info_request.text)
    
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

        if self.type == VideoInfo and VideoInfo.type == "pages":
            url = API.URL.bvid_url_api(bvid, str(self.index + 1))
        else:
            url = API.URL.bvid_url_api(bvid)

        copy_text(url)
    
    def copy_url_epid_EVT(self, event):
        epid = self.info_list.GetTextValue(self.index, 4)

        copy_text(API.URL.epid_url_api(epid))
    
    def copy_short_link_EVT(self, event):
        link = self.info_list.GetTextValue(self.index, 7)

        copy_text(link)
    
    def copy_durl_api_EVT(self, event):
        bvid = self.info_list.GetTextValue(self.index, 2)
        cid = self.info_list.GetTextValue(self.index, 5)

        if self.type == VideoInfo:
            durl_api = API.Video.download_api(bvid, cid)
        elif self.type == BangumiInfo:
            durl_api = API.Bangumi.download_api(bvid, cid)
        
        copy_text(durl_api)
