import wx
import wx.dataview

from utils.config import Config

class Frame(wx.Frame):
    def __init__(self, parent, title, size):
        wx.Frame.__init__(self, parent, -1, title)
        self.SetIcon(wx.Icon(Config._logo))

        self.SetSize(self.FromDIP((size)))

        self.panel = wx.Panel(self, -1)
        self.__center(parent)

    def __center(self, parent):
        parent_size, parent_pos, self_size = parent.GetSize(), parent.GetPosition(), self.GetSize()
        p_sx, p_sy, p_px, p_py, s_sx, s_sy = parent_size[0], parent_size[1], parent_pos[0], parent_pos[1], self_size[0], self_size[1]

        self.SetPosition((int((p_sx - s_sx) / 2) + p_px, int((p_sy - s_sy) / 2) + p_py))

class Dialog(wx.Dialog):
    def __init__(self, parent, title, size):
        wx.Dialog.__init__(self, parent, -1, title)
        self.SetSize(self.FromDIP((size)))

        self.panel = wx.Panel(self, -1)
        self.__center(parent)
        
    def __center(self, parent):
        parent_size, parent_pos, self_size = parent.GetSize(), parent.GetPosition(), self.GetSize()
        p_sx, p_sy, p_px, p_py, s_sx, s_sy = parent_size[0], parent_size[1], parent_pos[0], parent_pos[1], self_size[0], self_size[1]

        self.SetPosition((int((p_sx - s_sx) / 2) + p_px, int((p_sy - s_sy) / 2) + p_py))

class InfoBar(wx.InfoBar):
    def __init__(self, parent):
        wx.InfoBar.__init__(self, parent, -1)
    
    def ShowMessage(self, msg, flags=...):
        super().Dismiss()
        return super().ShowMessage(msg, flags)
