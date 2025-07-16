import wx

from utils.config import Config

from utils.common.thread import Thread

from utils.common.enums import ParseStatus, ParseType, StatusCode, EpisodeDisplayType, LiveStatus, Platform, ProcessingType, ExitOption

from utils.parse.live import LiveInfo, LiveParser

from gui.dialog.live import LiveRecordingWindow
from gui.dialog.confirm.duplicate import DuplicateDialog

from gui.component.window.frame import Frame

class MainWindow(Frame):
    def __init__(self, parent):
        def set_window_property():
            match Platform(Config.Sys.platform):
                case Platform.Windows | Platform.macOS:
                    self.SetSize(self.FromDIP((800, 450)))

                case Platform.Linux:
                    self.SetSize(self.FromDIP((900, 550)))
            
            self.CenterOnParent()

            if Config.Basic.remember_window_status:
                if Config.Basic.window_maximized:
                    self.Maximize()
                else:
                    if Config.Basic.window_size:
                        self.SetSize(Config.Basic.window_size)
                    
                    if Config.Basic.window_pos:
                        self.SetPosition(Config.Basic.window_pos)

        Frame.__init__(self, parent, Config.APP.name)

        set_window_property()

        self.get_sys_settings()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def onDownloadEVT(self, event):
        match self.current_parse_type:
            case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                def callback():
                    self.onOpenDownloadMgrEVT(event)

                if not self.episode_list.GetCheckedItemCount():
                    wx.MessageDialog(self, "下载失败\n\n请选择要下载的项目。", "警告", wx.ICON_WARNING).ShowModal()
                    return
                
                if Config.Basic.auto_popup_option_dialog:
                    if self.onShowDownloadOptionDlgEVT(event) != wx.ID_OK:
                        return
                
                self.episode_list.GetAllCheckedItem(self.current_parse_type, self.video_quality_id)

                duplicate_episode_list = self.download_window.find_duplicate_tasks(self.episode_list.download_task_info_list)

                if duplicate_episode_list:
                    if DuplicateDialog(self, duplicate_episode_list).ShowModal() != wx.ID_OK:
                        return

                Thread(target = self.download_window.add_to_download_list, args = (self.episode_list.download_task_info_list, callback, )).start()

                self.processing_window.ShowModal(ProcessingType.Process)

            case ParseType.Live:
                if LiveInfo.status == LiveStatus.Not_Started.value:
                    wx.MessageDialog(self, "直播间未开播\n\n当前直播间未开播，请开播后再进行解析", "警告", wx.ICON_WARNING).ShowModal()
                    return
                
                self.live_parser.get_live_stream(self.live_quality_id)
                
                LiveRecordingWindow(self).ShowModal()

    