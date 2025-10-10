import wx
import gettext

from utils.config import Config
from utils.common.enums import EpisodeDisplayType

from gui.id import ID

_ = gettext.gettext

class EpisodeOptionMenu(wx.Menu):
    def __init__(self, enable_in_section_option: bool = True):
        wx.Menu.__init__(self)

        single_menuitem = wx.MenuItem(self, ID.EPISODE_SINGLE_MENU, _("显示单个视频"), kind = wx.ITEM_RADIO)
        in_section_menuitem = wx.MenuItem(self, ID.EPISODE_IN_SECTION_MENU, _("显示视频所在的列表"), kind = wx.ITEM_RADIO)
        in_section_menuitem.Enable(enable_in_section_option)
        all_section_menuitem = wx.MenuItem(self, ID.EPISODE_ALL_SECTIONS_MENU, _("显示全部相关视频"), kind = wx.ITEM_RADIO)
        show_episode_full_name = wx.MenuItem(self, ID.EPISODE_FULL_NAME_MENU, _("显示完整剧集名称"), kind = wx.ITEM_CHECK)

        self.Append(wx.NewIdRef(), _("剧集列表显示设置"))
        self.AppendSeparator()
        self.Append(single_menuitem)
        self.Append(in_section_menuitem)
        self.Append(all_section_menuitem)
        self.AppendSeparator()
        self.Append(show_episode_full_name)

        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                single_menuitem.Check(True)

            case EpisodeDisplayType.In_Section:
                in_section_menuitem.Check(True)

            case EpisodeDisplayType.All:
                all_section_menuitem.Check(True)

        show_episode_full_name.Check(Config.Misc.show_episode_full_name)