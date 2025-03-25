import wx
import webbrowser

from utils.config import Config
from utils.common.thread import Thread
from utils.common.icon_v2 import IconManager, IconType
from utils.common.update import Update

from gui.window.download_v3 import DownloadManagerWindow
from gui.window.settings import SettingWindow

from gui.dialog.about import AboutWindow
from gui.dialog.changelog import ChangeLogDialog
from gui.dialog.update import UpdateWindow
from gui.dialog.converter import ConverterWindow
from gui.dialog.cut_clip import CutClipDialog

from gui.component.frame import Frame
from gui.component.panel import Panel
from gui.component.search_ctrl import SearchCtrl
from gui.component.tree_list import TreeListCtrl
from gui.component.button import Button
from gui.component.bitmap_button import BitmapButton

class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, Config.APP.name)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.init_id()

        icon_mgr = IconManager(self)

        panel = Panel(self)

        url_lab = wx.StaticText(panel, -1, "链接")
        self.url_box = SearchCtrl(panel, "在此处粘贴链接进行解析", search = False, clear = True)
        self.get_btn = wx.Button(panel, -1, "Get")

        url_hbox = wx.BoxSizer(wx.HORIZONTAL)
        url_hbox.Add(url_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        url_hbox.Add(self.url_box, 1, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.EXPAND, 10)
        url_hbox.Add(self.get_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)

        self.type_lab = wx.StaticText(panel, -1, "")
        self.video_quality_lab = wx.StaticText(panel, -1, "清晰度")
        self.video_quality_choice = wx.Choice(panel, -1)
        self.episode_option_btn = BitmapButton(panel, icon_mgr.get_icon_bitmap(IconType.LIST_ICON))
        self.episode_option_btn.Enable(False)
        self.download_option_btn = BitmapButton(panel, icon_mgr.get_icon_bitmap(IconType.SETTING_ICON))
        self.download_option_btn.Enable(False)

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.AddStretchSpacer()
        info_hbox.Add(self.video_quality_lab, 0, wx.ALL, 10)
        info_hbox.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)
        info_hbox.Add(self.episode_option_btn, 0, wx.ALL & (~wx.LEFT), 10)
        info_hbox.Add(self.download_option_btn, 0, wx.ALL & (~wx.LEFT), 10)

        self.episode_list = TreeListCtrl(panel)

        self.download_mgr_btn = Button(panel, "下载管理", size = self.get_scaled_size((100, 30)))
        self.download_btn = Button(panel, "开始下载", size = self.get_scaled_size((100, 30)))
        self.download_btn.Enable(False)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(url_hbox, 0, wx.EXPAND)
        vbox.Add(info_hbox, 0, wx.EXPAND)
        vbox.Add(self.episode_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        panel.SetSizerAndFit(vbox)

        self.Fit()

        self.init_menubar()

    def init_id(self):
        self.ID_LOGIN_MENU = wx.NewIdRef()
        self.ID_LOGOUT_MENU = wx.NewIdRef()
        self.ID_DEBUG_MENU = wx.NewIdRef()
        self.ID_CONVERTER_MENU = wx.NewIdRef()
        self.ID_CUT_CLIP_MENU = wx.NewIdRef()
        self.ID_SETTINGS_MENU = wx.NewIdRef()

        self.ID_CHECK_UPDATE_MENU = wx.NewIdRef()
        self.ID_CHANGELOG_MENU = wx.NewIdRef()
        self.ID_HELP_MENU = wx.NewIdRef()
        self.ID_FEEDBACK_MENU = wx.NewIdRef()
        self.ID_ABOUT_MENU = wx.NewIdRef()

    def init_menubar(self):
        menu_bar = wx.MenuBar()

        tool_manu = wx.Menu()
        help_menu = wx.Menu()

        if Config.User.login:
            tool_manu.Append(self.ID_LOGOUT_MENU, "注销(&L)")
        else:
            tool_manu.Append(self.ID_LOGIN_MENU, "登录(&L)")

        tool_manu.AppendSeparator()

        if Config.Misc.enable_debug:
            tool_manu.Append(self.ID_DEBUG_MENU, "调试(&D)")

        tool_manu.Append(self.ID_CONVERTER_MENU, "格式转换(&F)")
        tool_manu.Append(self.ID_CUT_CLIP_MENU, "截取片段(&I)")
        tool_manu.AppendSeparator()
        tool_manu.Append(self.ID_SETTINGS_MENU, "设置(&S)")

        help_menu.Append(self.ID_CHECK_UPDATE_MENU, "检查更新(&U)")
        help_menu.Append(self.ID_CHANGELOG_MENU, "更新日志(&P)")
        help_menu.AppendSeparator()
        help_menu.Append(self.ID_HELP_MENU, "使用帮助(&C)")
        help_menu.Append(self.ID_FEEDBACK_MENU, "意见反馈(&B)")
        help_menu.Append(self.ID_ABOUT_MENU, "关于(&A)")

        menu_bar.Append(tool_manu, "工具(&T)")
        menu_bar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menu_bar)

    def Bind_EVT(self):
        self.Bind(wx.EVT_MENU, self.onMenuEVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgrEVT)

    def init_utils(self):
        self.download_window = DownloadManagerWindow(self)

    def onMenuEVT(self, event):
        match event.GetId():
            case self.ID_CONVERTER_MENU:
                ConverterWindow(self).ShowModal()

            case self.ID_CUT_CLIP_MENU:
                CutClipDialog(self).ShowModal()

            case self.ID_SETTINGS_MENU:
                SettingWindow(self).ShowModal()

            case self.ID_CHECK_UPDATE_MENU:
                def check_update_thread():
                    Update.get_update()

                    if Config.Temp.update_json:
                        if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                            wx.CallAfter(UpdateWindow(self).ShowModal)
                        else:
                            wx.CallAfter(wx.MessageDialog(self, "当前没有可用的更新", "检查更新", wx.ICON_INFORMATION).ShowModal)
                    else:
                        wx.CallAfter(wx.MessageDialog(self, "检查更新失败\n\n当前无法检查更新，请稍候再试", "检查更新", wx.ICON_ERROR).ShowModal)

                Thread(target = check_update_thread).start()

            case self.ID_CHANGELOG_MENU:
                def changelog_thread():
                    Update.get_changelog()

                    if Config.Temp.changelog:
                        wx.CallAfter(ChangeLogDialog(self).ShowModal)
                    else:
                        wx.CallAfter(wx.MessageDialog(self, "获取更新日志失败\n\n当前无法获取更新日志，请稍候再试", "获取更新日志", wx.ICON_ERROR).ShowModal)

                Thread(target = changelog_thread).start()

            case self.ID_HELP_MENU:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/use/basic.html")

            case self.ID_FEEDBACK_MENU:
                webbrowser.open("https://github.com/ScottSloan/Bili23-Downloader/issues")

            case self.ID_ABOUT_MENU:
                AboutWindow(self).ShowModal()

    def onGetEVT(self, event):
        pass

    def onOpenDownloadMgrEVT(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()
            self.download_window.CenterOnParent()
        
        elif self.download_window.IsIconized():
            self.download_window.Iconize(False)
        
        self.download_window.SetFocus()
        self.download_window.downloading_page_btn.onClickEVT(event)