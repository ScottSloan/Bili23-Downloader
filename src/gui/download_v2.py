import io
import os
import wx
import time
import json
import requests
import subprocess
from typing import Dict, List, Callable

from gui.templates import Frame, ScrolledPanel
from gui.dialog.error import ErrorInfoDialog
from gui.dialog.cover import CoverViewerDialog

from utils.config import Config
from utils.data_type import DownloadTaskInfo, DownloaderCallback, DownloaderInfo, UtilsCallback, TaskPanelCallback, ErrorLog
from utils.icon_v2 import IconManager, RESUME_ICON, PAUSE_ICON, DELETE_ICON, FOLDER_ICON, RETRY_ICON
from utils.thread import Thread
from utils.tool_v2 import RequestTool, FileDirectoryTool, DownloadFileTool, FormatTool, UniversalTool
from utils.downloader import Downloader
from utils.parse.extra import ExtraInfo, ExtraParser
from utils.mapping import video_quality_mapping, audio_quality_mapping, video_codec_mapping, get_mapping_key_by_value

class DownloadManagerWindow(Frame):
    def __init__(self, parent):
        # 下载管理窗口
        Frame.__init__(self, parent, "下载管理", style = wx.DEFAULT_FRAME_STYLE & (~wx.MINIMIZE_BOX) & (~wx.MAXIMIZE_BOX))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)

                case "linux" | "darwin":
                    return wx.DefaultSize

        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")

        def _get_panel_size():
            match Config.Sys.platform:
                case "windows" | "darwin":
                    return self.FromDIP((800, 350))

                case "linux":
                    return self.FromDIP((850, 400))

        _set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 5))

        self.task_count_lab = wx.StaticText(self.panel, -1, "下载管理")
        self.task_count_lab.SetFont(font)

        max_download_lab = wx.StaticText(self.panel, -1, "并行下载数：")
        self.max_download_choice = wx.Choice(self.panel, -1, choices = [f"{i + 1}" for i in range(8)])
        self.max_download_choice.SetSelection(Config.Download.max_download_count - 1)

        self.start_all_btn = wx.Button(self.panel, -1, "全部开始")
        self.pause_all_btn = wx.Button(self.panel, -1, "全部暂停")
        self.stop_all_btn = wx.Button(self.panel, -1, "全部取消")

        top_bar_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_bar_hbox.Add(max_download_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        top_bar_hbox.Add(self.max_download_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        top_bar_hbox.AddStretchSpacer()
        top_bar_hbox.Add(self.start_all_btn, 0, wx.ALL & (~wx.TOP), 10)
        top_bar_hbox.Add(self.pause_all_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        top_bar_hbox.Add(self.stop_all_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        top_bar_border = wx.StaticLine(self.panel, -1, style = wx.LI_HORIZONTAL)

        self.download_task_list_panel = ScrolledPanel(self.panel, _get_panel_size())
        
        bottom_bar_border = wx.StaticLine(self.panel, -1, style = wx.LI_HORIZONTAL)

        self.open_download_directory_btn = wx.Button(self.panel, -1, "打开下载目录", size = _get_scale_size((100, 30)))
        self.clear_history_btn = wx.Button(self.panel, -1, "清除下载记录", size = _get_scale_size((100, 30)))

        bottom_bar_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_bar_hbox.Add(self.open_download_directory_btn, 0, wx.ALL, 10)
        bottom_bar_hbox.AddStretchSpacer()
        bottom_bar_hbox.Add(self.clear_history_btn, 0, wx.ALL, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.task_count_lab, 0, wx.ALL, 10)
        vbox.Add(top_bar_hbox, 0, wx.EXPAND)
        vbox.Add(top_bar_border, 0, wx.EXPAND)
        vbox.Add(self.download_task_list_panel, 1, wx.EXPAND)
        vbox.Add(bottom_bar_border, 0, wx.EXPAND)
        vbox.Add(bottom_bar_hbox, 0, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

        self.Fit()

    def Bind_EVT(self):
        # 绑定相关事件
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.max_download_choice.Bind(wx.EVT_CHOICE, self.onChangeMaxDownloaderEVT)

        self.start_all_btn.Bind(wx.EVT_BUTTON, self.onStartAllEVT)
        self.pause_all_btn.Bind(wx.EVT_BUTTON, self.onPauseAllEVT)
        self.stop_all_btn.Bind(wx.EVT_BUTTON, self.onStopAllEVT)

        self.open_download_directory_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadDirectoryEVT)
        self.clear_history_btn.Bind(wx.EVT_BUTTON, self.onClearHistoryEVT)

    def onCloseEVT(self, event):
        # 窗口关闭事件
        self.Hide()

    def onStartAllEVT(self, event):
        # 开始全部下载任务
        self.start_download()

    def onPauseAllEVT(self, event):
        # 暂停全部下载任务
        for panel in self.get_download_task_panel_list():
            if isinstance(panel, DownloadTaskPanel):
                if panel.task_info.status in Config.Type.DOWNLOAD_STATUS_ALIVE_LIST:
                    panel.onPause()

    def onStopAllEVT(self, event):
        # 取消全部下载任务
        self.download_task_list_panel.Freeze()

        for panel in self.get_download_task_panel_list():
            if isinstance(panel, DownloadTaskPanel):
                # EX 列表还包含了下载失败和合成失败两种情况，当前正在合成的视频或者正在转换的音频暂不支持取消
                if panel.task_info.status in Config.Type.DOWNLOAD_STATUS_ALIVE_LIST_EX:
                    panel.onStopEVT(event)

        self.download_task_list_panel.Thaw()

    def onChangeMaxDownloaderEVT(self, event):
        def _update_config():
            from utils.config import conf

            Config.Download.max_download_count = int(self.max_download_choice.GetStringSelection())

            conf.config.set("download", "max_download", str(Config.Download.max_download_count))

            conf.config_save()

        # 动态调整并行下载数
        _update_config()

        _count = 0

        for panel in self.get_download_task_panel_list():
            if isinstance(panel, DownloadTaskPanel):
                if panel.task_info.status in Config.Type.DOWNLOAD_STATUS_ALIVE_LIST:
                    # 处于等待、下载中、暂停三种状态
                    if self.get_download_task_count([Config.Type.DOWNLOAD_STATUS_DOWNLOADING]) < Config.Download.max_download_count:
                        # 当前下载数小于设置的并行下载数
                        if panel.task_info.status in [Config.Type.DOWNLOAD_STATUS_WAITING, Config.Type.DOWNLOAD_STATUS_PAUSE]:
                            # 等待和暂停的任务开始下载
                            panel.onResume()
                    else:
                        # 当前下载数大于设置的并行下载数
                        if panel.task_info.status == Config.Type.DOWNLOAD_STATUS_DOWNLOADING:
                            _count += 1
                            
                            if _count > Config.Download.max_download_count:
                                # 正在下载的任务暂停下载
                                panel.onPause()

    def onOpenDownloadDirectoryEVT(self, event):
        # 打开下载目录事件
        FileDirectoryTool.open_directory(Config.Download.path)
    
    def onClearHistoryEVT(self, event):
        # 清除已完成的下载记录
        self.download_task_list_panel.Freeze()

        for panel in self.get_download_task_panel_list():
            if isinstance(panel, DownloadTaskPanel):
                if panel.task_info.status == Config.Type.DOWNLOAD_STATUS_FINISHED:
                    panel.onStopEVT(event)

        self.download_task_list_panel.Thaw()

    def init_utils(self):
        # 记录下载任务的 cid 列表
        self._temp_cid_list = []

        # 读取断点续传信息
        self.load_download_task()

    def load_download_task(self):
        def empty_callback():
            pass

        _download_task_info_list = []

        # 读取断点续传信息
        for file in os.listdir(Config.User.download_file_directory):
            # 遍历下载目录
            file_path = os.path.join(Config.User.download_file_directory, file)

            # 判断是否为断点续传信息文件
            if os.path.isfile(file_path):
                if file.startswith("info_") and file.endswith(".json"):
                    download_file_tool = DownloadFileTool(file_name = file)
                    
                    # 检查文件兼容性
                    if not download_file_tool._check_compatibility():
                        download_file_tool.clear_download_info()
                        continue

                    _task_info = DownloadTaskInfo()
                    _task_info.load_from_dict(download_file_tool._read_download_file_json()["task_info"])

                    # 如果下载状态为等待下载，或者正在下载，则更新为暂停中
                    if _task_info.status in Config.Type.DOWNLOAD_STATUS_ALIVE_LIST:
                        _task_info.status = Config.Type.DOWNLOAD_STATUS_PAUSE

                    _download_task_info_list.append(_task_info)

        # 根据时间戳排序
        _download_task_info_list.sort(key = lambda _timestamp: _task_info.timestamp, reverse = False)

        wx.CallAfter(self.add_download_task_panel, _download_task_info_list, empty_callback, False)

    def start_download(self):
        # 开始下载
        for panel in self.get_download_task_panel_list():
            if isinstance(panel, DownloadTaskPanel):
                if panel.task_info.status in [Config.Type.DOWNLOAD_STATUS_WAITING, Config.Type.DOWNLOAD_STATUS_PAUSE]:
                    if self.get_download_task_count([Config.Type.DOWNLOAD_STATUS_DOWNLOADING]) < Config.Download.max_download_count:
                        panel.onResume()

    def get_download_task_panel_list(self):
        # 获取下载列表项 (DownloadTaskPanel)，供遍历
        children: List[DownloadTaskPanel] = self.download_task_list_panel.GetChildren()
        
        return children
    
    def get_download_task_count(self, condition: List[int]):
        # 统计正在下载的任务数
        _count = 0

        for panel in self.get_download_task_panel_list():
            if isinstance(panel, DownloadTaskPanel):
                if panel.task_info.status in condition:
                    _count += 1

        return _count

    def add_download_task_panel(self, download_task_info_list: List[DownloadTaskInfo], callback: Callable, start_download: bool):
        def worker(info: DownloadTaskInfo, multiple_flag: bool, index: int):
            if multiple_flag:
                info.index = index + 1

            task_panel_callback = TaskPanelCallback()
            task_panel_callback.onStartNextCallback = self.start_download
            task_panel_callback.onStopCallbacak = stop_download_callback
            task_panel_callback.onUpdateTaskCountCallback = self.update_task_count_label

            item = DownloadTaskPanel(self.download_task_list_panel, info, task_panel_callback)

            # 添加进 cid 列表记录
            self._temp_cid_list.append(info.cid)

            return  (item, 0, wx.EXPAND)

        def stop_download_callback(cid: int):
            # 停止下载回调函数
            self.refresh_task_list_panel_ui()

            # 清除 cid 列表中的记录
            self._temp_cid_list.remove(cid)
        
        task_panel_list = []

        # 批量下载标识符
        multiple_flag = len(download_task_info_list) > 1

        # 暂时停止 UI 更新
        self.download_task_list_panel.Freeze()

        for index, info in enumerate(download_task_info_list):
            # 检查 cid 列表是否已包含，防止重复下载
            if info.cid not in self._temp_cid_list:
                info.timestamp += index
                task_panel_list.append(worker(info, multiple_flag, index))

        self.download_task_list_panel.sizer.AddMany(task_panel_list)

        # 恢复 UI 更新
        self.download_task_list_panel.Thaw()

        self.refresh_task_list_panel_ui()

        # 下载任务添加完毕，回调函数
        callback()

        if start_download:
            self.start_download()

    def update_task_count_label(self):
        count = self.get_download_task_count(Config.Type.DOWNLOAD_STATUS_ALIVE_LIST)

        if count:
            _label = f"{count} 个任务正在下载"
        else:
            _label = "下载管理"

        self.task_count_lab.SetLabel(_label)

    def refresh_task_list_panel_ui(self):
        # 刷新面板 ui
        self.download_task_list_panel.Layout()
        self.download_task_list_panel.SetupScrolling(scroll_x = False, scrollToTop = False)

        wx.CallAfter(self.update_task_count_label)

class DownloadUtils:
    def __init__(self, task_info: DownloadTaskInfo, callback: UtilsCallback):
        self.task_info, self.callback = task_info, callback

    def get_video_bangumi_download_url(self):
        def get_json():
            def request_get(url: str):
                req = requests.get(url, headers = RequestTool.get_headers(self.task_info.referer_url, Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
                return json.loads(req.text)
        
            match self.task_info.download_type:
                case Config.Type.VIDEO:
                    url = f"https://api.bilibili.com/x/player/playurl?bvid={self.task_info.bvid}&cid={self.task_info.cid}&qn=0&fnver=0&fnval=4048&fourk=1"

                    json_dash = request_get(url)

                    return json_dash["data"]["dash"]
                
                case Config.Type.BANGUMI:
                    url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={self.task_info.bvid}&cid={self.task_info.cid}&qn=0&fnver=0&fnval=12240&fourk=1"

                    json_dash = request_get(url)

                    return json_dash["result"]["dash"]
        
        def get_video_available_quality():
            # 获取视频最高清晰度
            
            if self.task_info.video_quality_id == 200:
                highest_video_quality_id = self._get_highest_video_quality(json_dash["video"], without_dolby = not Config.Download.enable_dolby)

                self.task_info.video_quality_id = highest_video_quality_id
            else:
                highest_video_quality_id = self._get_highest_video_quality(json_dash["video"])
                if highest_video_quality_id < self.task_info.video_quality_id:
                    # 当视频不存在选取的清晰度时，选取最高可用的清晰度
                    self.task_info.video_quality_id = highest_video_quality_id
                else:
                    self.task_info.video_quality_id = self.task_info.video_quality_id

        def get_video_available_codec():
            def get_codec_index(data: List[dict]):
                for index, entry in enumerate(data):
                    if entry["codecid"] == self.task_info.video_codec_id:
                        return index

            # 获取选定清晰度的视频列表，包含多种清晰度
            temp_video_durl_list = [i for i in json_dash["video"] if i["id"] == self.task_info.video_quality_id]

            self.task_info.video_codec_id = Config.Download.video_codec_id

            codec_index = get_codec_index(temp_video_durl_list)

            # 判断视频支持选定的编码
            if codec_index is not None:
                durl_json = temp_video_durl_list[codec_index]

            else:
                # 不支持选定编码，自动切换到 H264
                durl_json = temp_video_durl_list[0]
                self.task_info.video_codec_id = 7

            self._video_download_url_list = self._get_all_available_download_url_list(durl_json)

        def get_audio_available_quality():
            def _get_flac(_json_dash: Dict):
                # 无损
                if "flac" in _json_dash:
                    if _json_dash["flac"]:
                        if "audio" in _json_dash["flac"]:
                            if _json_dash["flac"]["audio"]:
                                audio_node = _json_dash["flac"]["audio"]

                                self._audio_download_url_list = self._get_all_available_download_url_list(audio_node)

                                self.task_info.audio_type = "flac"
                                self.task_info.audio_quality_id = 30251

            def _get_dolby(_json_dash: Dict):
                # 杜比全景声
                if "dolby" in _json_dash:
                    if _json_dash["dolby"]:
                        if "audio" in _json_dash["dolby"]:
                            if _json_dash["dolby"]["audio"]:
                                audio_node = _json_dash["dolby"]["audio"][0]

                                self._audio_download_url_list = self._get_all_available_download_url_list(audio_node)

                                self.task_info.audio_type = "ec3"
                                self.task_info.audio_quality_id = 30250
                                    
            if json_dash["audio"]:
                match self.task_info.audio_quality_id:
                    case 30300:
                        _get_flac(json_dash)

                        if Config.Download.enable_dolby:
                            _get_dolby(json_dash)

                    case 30251:
                        _get_flac(json_dash)

                    case 30250:
                        _get_dolby(json_dash)

                    case _:
                        self._get_default_audio_download_url(json_dash["audio"])

                if not self._audio_download_url_list:
                    self._get_default_audio_download_url(json_dash["audio"])

            else:
                # 视频不存在音频，标记 flag 为仅下载视频
                self.task_info.video_merge_type = Config.Type.MERGE_TYPE_VIDEO

        json_dash = get_json()

        self._video_download_url_list = self._audio_download_url_list = []

        get_video_available_quality()

        get_video_available_codec()

        get_audio_available_quality()
    
    def get_downloader_info_list(self):
        self.get_video_bangumi_download_url()

        _temp_info = []

        match self.task_info.video_merge_type:
            case Config.Type.MERGE_TYPE_ALL:
                _temp_info.append(self._get_video_downloader_info())
                _temp_info.append(self._get_audio_downloader_info())

            case Config.Type.MERGE_TYPE_VIDEO:
                _temp_info.append(self._get_video_downloader_info())
            
            case Config.Type.MERGE_TYPE_AUDIO:
                _temp_info.append(self._get_audio_downloader_info())

        return _temp_info

    def merge_video(self):
        def get_temp_file_name():
            self._temp_video_file_name = f"video_{self.task_info.id}.m4s"
            self._temp_audio_file_name = f"audio_{self.task_info.id}.{self.task_info.audio_type}"

        def clear_files():
            if Config.Merge.auto_clean:
                UniversalTool.remove_files(Config.Download.path, [self._temp_video_file_name, self._temp_audio_file_name, self._temp_out_file_name])

        get_temp_file_name()

        _cmd = self._get_shell_cmd()

        _process = self._run_subprocess(_cmd)

        if _process.returncode == 0:
            # 视频合成完毕，清理文件并回调函数
            clear_files()

            self.callback.onMergeFinishCallback()
        else:
            _error_log = ErrorLog()
            _error_log.log = _process.stdout
            _error_log.return_code = _process.returncode
            _error_log.time = UniversalTool.get_current_time()

            self.callback.onErrorCallback(_error_log)

    def _get_shell_cmd(self):
        def _get_audio_cmd():
            match self.task_info.audio_type:
                case "m4a" | "ec3":
                    if Config.Merge.m4a_to_mp3 and self.task_info.audio_type == "m4a":
                        return f'"{Config.FFmpeg.path}" -y -i "{self._temp_audio_file_name}" -c:a libmp3lame -q:a 0 "{self.file_title}.mp3"'
                    else:
                        return f'{_rename_cmd} "{self._temp_audio_file_name}" {_extra}"{self.full_file_name}"'
                
                case "flac":
                    return f'"{Config.FFmpeg.path}" -y -i "{self._temp_audio_file_name}" -c:a flac -q:a 0 "{self.file_title}.flac"'
        
        def override_file(_file_name_list):
            # 覆盖文件
            if Config.Merge.override_file:
                UniversalTool.remove_files(Config.Download.path, _file_name_list)

        match Config.Sys.platform:
            case "windows":
                _rename_cmd = "rename"
                _extra = ""

            case "linux":
                _rename_cmd = "mv"
                _extra = "-- "

            case "darwin":
                _rename_cmd = "mv"
                _extra = ""

        match self.task_info.video_merge_type:
            case Config.Type.MERGE_TYPE_ALL:
                _cmd = f'"{Config.FFmpeg.path}" -y -i "{self._temp_video_file_name}" -i "{self._temp_audio_file_name}" -acodec copy -vcodec copy -strict experimental {self._temp_out_file_name} && {_rename_cmd} {self._temp_out_file_name} {_extra}"{self.full_file_name}"'

            case Config.Type.MERGE_TYPE_VIDEO:
                _cmd = f'{_rename_cmd} "{self._temp_video_file_name}" {_extra}"{self.full_file_name}"'

            case Config.Type.MERGE_TYPE_AUDIO:
                _cmd = _get_audio_cmd()

        override_file([self.full_file_name])

        return _cmd

    def _run_subprocess(self, cmd: str):
        return subprocess.run(cmd, cwd = Config.Download.path, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True)

    def _get_video_downloader_info(self):
        info = DownloaderInfo()
        info.url_list = self._video_download_url_list
        info.type = "video"
        info.file_name = f"video_{self.task_info.id}.m4s"

        self._temp_video_file_name = info.file_name

        return info.to_dict()

    def _get_audio_downloader_info(self):
        info = DownloaderInfo()
        info.url_list = self._audio_download_url_list
        info.type = "audio"
        info.file_name = f"audio_{self.task_info.id}.{self.task_info.audio_type}"

        self._temp_audio_file_name = info.file_name

        return info.to_dict()
        
    def _get_default_audio_download_url(self, data: List[dict]):
        highest_audio_quality = self._get_highest_audio_quality(data)

        if highest_audio_quality < self.task_info.audio_quality_id or self.task_info.audio_quality_id == 30300:
            # 当视频不存在选取的音质时，选取最高可用的音质
            audio_quality = highest_audio_quality
        else:
            audio_quality = self.task_info.audio_quality_id

        temp_audio_durl = [i for i in data if i["id"] == audio_quality]

        self._audio_download_url_list = self._get_all_available_download_url_list(temp_audio_durl[0])

        self.task_info.audio_type = "m4a"
        self.task_info.audio_quality_id = audio_quality

    def _get_all_available_download_url_list(self, entry: dict):
        # 取视频音频的所有下载链接
        temp_list = []

        node_list = ["backupUrl", "backup_url", "baseUrl", "base_url"]

        for node_name in node_list:
            if node_name in entry:
                # 判断是否为列表
                if isinstance(entry[node_name], list):
                    temp_list.extend(entry[node_name])
                
                else:
                    temp_list.append(entry[node_name])

        return temp_list

    def _get_highest_video_quality(self, data: List[dict], without_dolby: bool = False):
        # 默认为 360P
        highest_video_quality_id = 16

        for entry in data:
            # 遍历列表，选取其中最高的清晰度
            if without_dolby and entry["id"] == 126:
                continue

            if entry["id"] > highest_video_quality_id:
                highest_video_quality_id = entry["id"]

        return highest_video_quality_id

    def _get_highest_audio_quality(self, data: List[dict]):
        # 默认为 64K
        highest_audio_quality = 30216

        for entry in data:
            if entry["id"] > highest_audio_quality:
                highest_audio_quality = entry["id"]

        return highest_audio_quality

    @property
    def file_title(self):
        if self.task_info.index:
            return f"{self.task_info.index} - {self.task_info.title_legal}"
        else:
            return self.task_info.title_legal

    @property
    def full_file_name(self):
        match self.task_info.video_merge_type:
            case Config.Type.MERGE_TYPE_ALL | Config.Type.MERGE_TYPE_VIDEO:
                return f"{self.file_title}.mp4"

            case Config.Type.MERGE_TYPE_AUDIO:
                if self.task_info.audio_type == "m4a" and Config.Merge.m4a_to_mp3:
                    return f"{self.file_title}.mp3"
                else:
                    return f"{self.file_title}.{self.task_info.audio_type}"

    @property
    def _temp_out_file_name(self):
        return f"out_{self.task_info.id}.mp4"

class DownloadTaskPanel(wx.Panel):
    def __init__(self, parent, info: DownloadTaskInfo, callback: TaskPanelCallback):
        self.task_info, self.callback = info, callback

        # 下载任务面板
        wx.Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        def _set_dark_mode(_control: wx.Control):
            if not Config.Sys.dark_mode:
                _control.SetForegroundColour(wx.Colour(108, 108, 108))

        def _get_button_scale_size():
            match Config.Sys.platform:
                case "windows" | "darwin":
                    return self.FromDIP((24, 24))
 
                case "linux":
                    return self.FromDIP((32, 32))

        def _get_progress_scale_size():
            match Config.Sys.platform:
                case "windows" | "linux":
                    return (-1, -1)
                
                case "darwin":
                    return self.FromDIP((120, 18))

        def _get_style():
            match Config.Sys.platform:
                case "windows" | "darwin":
                    return 0
                
                case "linux":
                    return wx.NO_BORDER

        # 初始化 UI
        self.icon_manager = IconManager(self.GetDPIScaleFactor())

        self.cover_bmp = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))
        self.cover_bmp.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.title_lab = wx.StaticText(self, -1, self.task_info.title, size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_MIDDLE)
        self.title_lab.SetToolTip(self.task_info.title)

        self.video_quality_lab = wx.StaticText(self, -1, "--", size = self.FromDIP((-1, -1)))
        _set_dark_mode(self.video_quality_lab)

        self.video_codec_lab = wx.StaticText(self, -1, "--", size = self.FromDIP((-1, -1)))
        _set_dark_mode(self.video_codec_lab)

        self.video_size_lab = wx.StaticText(self, -1, "--", size = self.FromDIP((-1, -1)))
        _set_dark_mode(self.video_size_lab)

        video_info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        video_info_hbox.Add(self.video_quality_lab, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.video_codec_lab, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.video_size_lab, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        video_info_vbox = wx.BoxSizer(wx.VERTICAL)
        video_info_vbox.AddSpacer(5)
        video_info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, 10)
        video_info_vbox.AddStretchSpacer()
        video_info_vbox.Add(video_info_hbox, 0, wx.EXPAND)
        video_info_vbox.AddSpacer(5)

        self.progress_bar = wx.Gauge(self, -1, 100, size = _get_progress_scale_size(), style = wx.GA_SMOOTH)

        progress_bar_hbox = wx.BoxSizer(wx.HORIZONTAL)
        progress_bar_hbox.Add(self.progress_bar, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)

        self.speed_lab = wx.StaticText(self, -1, "等待下载...", size = self.FromDIP((-1, -1)))
        _set_dark_mode(self.speed_lab)

        speed_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_hbox.Add(self.speed_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        progress_bar_vbox = wx.BoxSizer(wx.VERTICAL)
        progress_bar_vbox.AddSpacer(5)
        progress_bar_vbox.Add(progress_bar_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddStretchSpacer()
        progress_bar_vbox.Add(speed_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddSpacer(5)

        self.pause_btn = wx.BitmapButton(self, -1, self.get_button_icon(RESUME_ICON), size = _get_button_scale_size(), style = _get_style())
        self.pause_btn.SetToolTip("开始下载")

        self.stop_btn = wx.BitmapButton(self, -1, self.get_button_icon(DELETE_ICON), size = _get_button_scale_size(), style = _get_style())
        self.stop_btn.SetToolTip("取消下载")

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(self.cover_bmp, 0, wx.ALL, 10)
        panel_hbox.Add(video_info_vbox, 0, wx.EXPAND)
        panel_hbox.AddStretchSpacer()
        panel_hbox.Add(progress_bar_vbox, 0, wx.EXPAND)
        panel_hbox.Add(self.pause_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.Add(self.stop_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.AddSpacer(10)

        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.panel_vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        self.panel_vbox.Add(bottom_border, 0, wx.EXPAND)

        self.SetSizer(self.panel_vbox)

    def Bind_EVT(self):
        self.pause_btn.Bind(wx.EVT_BUTTON, self.onPauseResumeEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

        self.cover_bmp.Bind(wx.EVT_LEFT_UP, self.onShowCoverViewerDialogEVT)
        self.speed_lab.Bind(wx.EVT_LEFT_UP, self.onShowErrorInfoDialogEVT)

    def init_utils(self):
        def show_cover():
            def _is_16_9(_image: wx.Image):
                width, height = _image.GetSize()

                return (width / height) == (16 / 9)

            def resize_to_16_9(_image: wx.Image):
                # 将非 16:9 封面调整为 16:9
                width, height = _image.GetSize()

                new_height = int(width * (9 / 16))

                y_offset = (height - new_height) // 2

                return _image.GetSubImage(wx.Rect(0, y_offset, width, new_height))
            
            scale = self.FromDIP((112, 63))

            self._cover_raw_contents = RequestTool.request(self.task_info.cover_url)

            # 获取封面数据并保存为 wx.Image 对象
            temp_image = wx.Image(io.BytesIO(self._cover_raw_contents))

            # 非 16:9 封面，进行裁剪
            if not _is_16_9(temp_image):
                temp_image = resize_to_16_9(temp_image)
            
            # 裁剪图片至合适大小
            temp_image: wx.Image = temp_image.Scale(scale[0], scale[1], wx.IMAGE_QUALITY_HIGH)

            wx.CallAfter(set_cover, temp_image)

        def set_cover(image: wx.Image):
            # 设置封面
            self.cover_bmp.SetBitmap(image.ConvertToBitmap())

            self.panel_vbox.Layout()
        
        def get_downloader_callback():
            _callback = DownloaderCallback()
            _callback.onStartCallback = self.onStart
            _callback.onDownloadCallback = self.onDownload
            _callback.onMergeCallback = self.onMerge
            _callback.onErrorCallback = self.onDownloadFailed

            return _callback

        def get_utils_callback():
            _callback = UtilsCallback()
            _callback.onMergeFinishCallback = self.onMergeFinish
            _callback.onErrorCallback = self.onMergeFailed

            return _callback

        self._parent_download_manager = self.GetParent().GetParent().GetParent()
        self._cover_raw_contents = None

        # 获取视频封面
        if self.task_info.cover_url:
            Thread(target = show_cover).start()

        # 初始化断点续传工具类，并保存信息
        self.download_file_tool = DownloadFileTool(self.task_info.id)
        self.download_file_tool.save_download_info(self.task_info)
        
        self.downloader = Downloader(self.task_info, self.download_file_tool, get_downloader_callback())

        self.utils = DownloadUtils(self.task_info, get_utils_callback())

        self.load_download_task_info()

    def load_download_task_info(self):
        # 读取断点续传信息

        # 更新下载状态
        self.update_download_status(self.task_info.status)

        if self.task_info.completed_size:
            # 载入下载进度和下载状态
            self.progress_bar.SetValue(self.task_info.progress)

            self.show_media_info()

    def onPauseResumeEVT(self, event):
        # 暂停继续事件
        match self.task_info.status:
            case Config.Type.DOWNLOAD_STATUS_WAITING:
                # 等待下载的任务，开始下载
                self.start_download()

            case Config.Type.DOWNLOAD_STATUS_DOWNLOADING:
                # 正在下载的任务，暂停
                self.onPause()

            case Config.Type.DOWNLOAD_STATUS_PAUSE:
                # 暂停的任务，恢复下载
                self.onResume()

            case Config.Type.DOWNLOAD_STATUS_MERGING:
                # 正在合成的任务，合成
                self.onMerge()

            case Config.Type.DOWNLOAD_STATUS_FINISHED:
                # 下载完成的任务，打开文件所在位置
                self.onOpenLocation()

            case Config.Type.DOWNLOAD_STATUS_DOWNLOAD_FAILED | Config.Type.DOWNLOAD_STATUS_MERGE_FAILED:
                # 下载失败或合成失败，重试
                self.onResume()

        if not Config.Sys.dark_mode:
            self.speed_lab.SetForegroundColour(wx.Colour(108, 108, 108))
    
    def onPause(self):
        # 暂停下载
        self.downloader.onPause()
        
        # 更新下载状态为暂停中
        self.update_download_status(Config.Type.DOWNLOAD_STATUS_PAUSE)

    def onResume(self):
        # 继续下载

        if self.task_info.status != Config.Type.DOWNLOAD_STATUS_DOWNLOADING:
            if self.task_info.progress == 100:
                # 下载完成，合成视频
                self.onMerge()
            else:
                self.start_download()

    def onStopEVT(self, event):
        def worker():
            # 清除本地残留文件
            time.sleep(2.5)

            if hasattr(self.utils, "_temp_video_file_name"):
                UniversalTool.remove_files(Config.Download.path, [self.utils._temp_video_file_name, self.utils._temp_audio_file_name, self.utils._temp_out_file_name])

        # 停止下载，删除下载任务
        self.downloader.onStop()

        self.Hide()

        # 销毁下载任务面板，并清除断点续传信息
        self.Destroy()
        
        # 回调函数，刷新 UI
        self.callback.onStopCallbacak(self.task_info.cid)

        self.download_file_tool.clear_download_info()

        Thread(target = worker).start()

    def onStart(self, total_size: int):
        def callback():
        # 开始下载回调函数
            self.task_info.total_size = total_size

            self.speed_lab.SetLabel("")
            
            self.show_media_info()

            kwargs = {
                "total_size": total_size,
                "video_quality_id": self.utils.task_info.video_quality_id,
                "video_codec_id": self.utils.task_info.video_codec_id,
                "audio_quality_id": self.utils.task_info.audio_quality_id,
                "audio_type": self.utils.task_info.audio_type,
                "video_merge_type": self.utils.task_info.video_merge_type
            }

            self.download_file_tool.update_task_info_kwargs(**kwargs)
        
        wx.CallAfter(callback)

    def onDownload(self, info: dict):
        def callback():
            # 更新下载进度回调函数
            self.progress_bar.SetValue(info["progress"])

            if self.task_info.status == Config.Type.DOWNLOAD_STATUS_DOWNLOADING:
                # 只有在下载状态时才更新下载速度
                self.speed_lab.SetLabel(FormatTool.format_speed(info["speed"]))

            self.video_size_lab.SetLabel("{}/{}".format(FormatTool.format_size(info["completed_size"]), FormatTool.format_size(self.task_info.total_size)))
                
            self.task_info.progress = info["progress"]
            self.task_info.completed_size = info["completed_size"]
        
        wx.CallAfter(callback)

    def onMerge(self):
        def callback():
            # 合成视频回调函数
            self.show_media_info()

            self.callback.onUpdateTaskCountCallback()

            self.pause_btn.SetBitmap(self.get_button_icon(PAUSE_ICON))
            self.pause_btn.Enable(False)
            self.stop_btn.Enable(False)

            if self.task_info.video_merge_type == Config.Type.MERGE_TYPE_AUDIO:
                self.speed_lab.SetLabel("正在转换音频...")
            else:
                self.speed_lab.SetLabel("正在合成视频...")

            self.callback.onStartNextCallback()
        
        self.update_download_status(Config.Type.DOWNLOAD_STATUS_MERGING)

        wx.CallAfter(callback)

        Thread(target = self.utils.merge_video).start()

    def onMergeFinish(self):
        def callback():
            self.update_download_status(Config.Type.DOWNLOAD_STATUS_FINISHED)
            self.pause_btn.Enable(True)
            self.stop_btn.Enable(True)

            self.speed_lab.SetLabel("下载完成")
            self.speed_lab.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))

            if Config.Download.delete_history:
                self.download_file_tool.clear_download_info()

            _get_extra()

        def _get_extra():
            def _get_cover():
                _path = os.path.join(Config.Download.path, f"{self.utils.file_title}.jpg")

                with open(_path, "wb") as f:
                    f.write(self._cover_raw_contents)

            # 下载完成后，才进行下载附加内容
            extra_parser = ExtraParser(self.utils.file_title, self.task_info.cid, self.task_info.duration)
            
            if ExtraInfo.get_danmaku:
                extra_parser.get_danmaku()

            if ExtraInfo.get_cover:
                _get_cover()

        wx.CallAfter(callback)

    def onMergeFailed(self, error_log: ErrorLog):
        def callback():
            # 合成失败回调函数
            self.update_download_status(Config.Type.DOWNLOAD_STATUS_MERGE_FAILED)

            if self.task_info.video_merge_type == Config.Type.MERGE_TYPE_AUDIO:
                self.speed_lab.SetLabel("音频转换失败，点击查看详情")
            else:
                self.speed_lab.SetLabel("视频合成失败，点击查看详情")

            self.speed_lab.SetForegroundColour(wx.Colour("red"))
            self.speed_lab.SetCursor(wx.Cursor(wx.CURSOR_HAND))

            self.pause_btn.Enable(True)
            self.stop_btn.Enable(True)
        
        self._error_log = error_log

        wx.CallAfter(callback)

    def onDownloadFailed(self):
        def callback():
            # 下载失败回调函数
            self.update_download_status(Config.Type.DOWNLOAD_STATUS_DOWNLOAD_FAILED)
            self.speed_lab.SetLabel("下载失败")

            self.callback.onUpdateTaskCountCallback()
            self.callback.onStartNextCallback()

        wx.CallAfter(callback)
    
    def onOpenLocation(self):
        path = os.path.join(Config.Download.path, self.utils.full_file_name)

        FileDirectoryTool.open_file_location(path)

    def onShowErrorInfoDialogEVT(self, event):
        if hasattr(self, "_error_log") and self.task_info.status == Config.Type.DOWNLOAD_STATUS_MERGE_FAILED:
            dlg = ErrorInfoDialog(self._parent_download_manager, self._error_log)
            dlg.ShowModal()

    def onShowCoverViewerDialogEVT(self, event):
        dlg = CoverViewerDialog(self._parent_download_manager, self._cover_raw_contents)
        dlg.Show()

    def start_download(self):
        def worker():
            # 开始下载
            downloader_info_list = self.utils.get_downloader_info_list()

            self.downloader.start_download(downloader_info_list)

        # 更新下载状态为正在下载
        self.update_download_status(Config.Type.DOWNLOAD_STATUS_DOWNLOADING)

        Thread(target = worker).start()

    def show_media_info(self):
        if self.task_info.progress == 100:
            self.video_size_lab.SetLabel(FormatTool.format_size(self.task_info.total_size))
        else:
            self.video_size_lab.SetLabel(f"{FormatTool.format_size(self.task_info.completed_size)}/{FormatTool.format_size(self.task_info.total_size)}")

        match self.task_info.video_merge_type:
            case Config.Type.MERGE_TYPE_ALL | Config.Type.MERGE_TYPE_VIDEO:
                self.video_quality_lab.SetLabel(get_mapping_key_by_value(video_quality_mapping, self.utils.task_info.video_quality_id))
                self.video_codec_lab.SetLabel(get_mapping_key_by_value(video_codec_mapping, self.utils.task_info.video_codec_id))

            case Config.Type.MERGE_TYPE_AUDIO:
                self.video_quality_lab.SetLabel("音频")
                self.video_codec_lab.SetLabel(get_mapping_key_by_value(audio_quality_mapping, self.utils.task_info.audio_quality_id))

    def update_download_status(self, status: int):
        def update_btn_icon():
            match self.task_info.status:
                case Config.Type.DOWNLOAD_STATUS_DOWNLOADING:
                    # 正在下载，显示暂停图标
                    self.pause_btn.SetBitmap(self.get_button_icon(PAUSE_ICON))

                    self.pause_btn.SetToolTip("暂停下载")
                    self.speed_lab.SetLabel("正在获取下载信息...")

                case Config.Type.DOWNLOAD_STATUS_PAUSE:
                    # 暂停中，显示继续下载图标
                    self.pause_btn.SetBitmap(self.get_button_icon(RESUME_ICON))

                    self.pause_btn.SetToolTip("继续下载")
                    self.speed_lab.SetLabel("暂停中")

                case Config.Type.DOWNLOAD_STATUS_MERGE_FAILED:
                    # 合成失败，显示重试图标
                    self.pause_btn.SetBitmap(self.get_button_icon(RETRY_ICON))

                    self.pause_btn.SetToolTip("重试")

                    if self.task_info.video_merge_type == Config.Type.MERGE_TYPE_AUDIO:
                        self.speed_lab.SetLabel("音频转换失败")
                    else:
                        self.speed_lab.SetLabel("视频合成失败")

                    self.speed_lab.SetForegroundColour(wx.Colour("red"))

                case Config.Type.DOWNLOAD_STATUS_DOWNLOAD_FAILED:
                    # 下载失败，显示重试图标
                    self.pause_btn.SetBitmap(self.get_button_icon(RETRY_ICON))

                    self.pause_btn.SetToolTip("重试")
                    self.speed_lab.SetLabel("下载失败")
                    self.speed_lab.SetForegroundColour(wx.Colour("red"))

                case Config.Type.DOWNLOAD_STATUS_FINISHED:
                    # 下载完成，显示打开文件所在位置图标
                    self.pause_btn.SetBitmap(self.get_button_icon(FOLDER_ICON))

                    self.pause_btn.SetToolTip("打开文件所在位置")
                    self.speed_lab.SetLabel("下载完成")

                    self.stop_btn.SetToolTip("清除记录")

        # 更新下载状态
        self.task_info.status = status

        update_btn_icon()

        kwargs = {
            "status": status
        }

        # 同步更新到文件
        self.download_file_tool.update_task_info_kwargs(**kwargs)

    def get_button_icon(self, icon_id: int):
        # 获取按钮位图图标
        image = wx.Image(io.BytesIO(self.icon_manager.get_icon_bytes(icon_id)))

        return image.ConvertToBitmap()
