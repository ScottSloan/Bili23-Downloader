import wx
import gettext

from gui.id import ID

_ = gettext.gettext

class EpisodeListMenu(wx.Menu):
    def __init__(self, item_type: str, checked_state: bool, collapsed_state: bool):
        wx.Menu.__init__(self)

        view_cover_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_VIEW_COVER_MENU, _("查看视频封面(&V)"))
        copy_title_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_COPY_TITLE_MENU, _("复制标题名称(&C)"))
        copy_url_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_COPY_URL_MENU, _("复制视频链接(&U)"))
        open_in_browser_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_OPEN_IN_BROWSER_MENU, _("在浏览器中打开(&B)"))
        edit_title_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_EDIT_TITLE_MENU, _("修改标题名称(&E)"))
        check_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_CHECK_MENU, _("取消选择(&N)") if checked_state else _("选择(&S)"))
        collapse_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_COLLAPSE_MENU, _("展开(&X)") if collapsed_state else _("折叠(&O)"))
        select_batch_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_SELECT_BATCH_MENU, _("批量选取项目(&P)"))
        refresh_media_info_menuitem = wx.MenuItem(self, ID.EPISODE_LIST_REFRESH_MEDIA_INFO_MENU, _("刷新媒体信息(&R)"))

        self.Append(view_cover_menuitem)
        self.AppendSeparator()
        self.Append(copy_title_menuitem)
        self.Append(copy_url_menuitem)
        self.Append(open_in_browser_menuitem)
        self.AppendSeparator()
        self.Append(edit_title_menuitem)
        self.AppendSeparator()
        self.Append(check_menuitem)
        self.Append(collapse_menuitem)
        self.AppendSeparator()
        self.Append(select_batch_menuitem)
        self.Append(refresh_media_info_menuitem)

        if item_type == "node":
            self.Enable(ID.EPISODE_LIST_VIEW_COVER_MENU, False)
            self.Enable(ID.EPISODE_LIST_COPY_URL_MENU, False)
            self.Enable(ID.EPISODE_LIST_OPEN_IN_BROWSER_MENU, False)
            self.Enable(ID.EPISODE_LIST_EDIT_TITLE_MENU, False)
            self.Enable(ID.EPISODE_LIST_REFRESH_MEDIA_INFO_MENU, False)
        else:
            self.Enable(ID.EPISODE_LIST_COLLAPSE_MENU, False)
