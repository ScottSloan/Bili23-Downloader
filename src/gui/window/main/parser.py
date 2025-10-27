import wx
import gettext

from utils.config import Config

from utils.common.regex import Regex
from utils.common.enums import ParseType, ParseStatus, StatusCode
from utils.common.model.callback import ParseCallback
from utils.common.model.list_item_info import TreeListItemInfo
from utils.common.thread import Thread
from utils.common.exception import GlobalException, show_error_message_dialog
from utils.common.map import url_pattern_map

from utils.parse.video import VideoParser
from utils.parse.bangumi import BangumiParser
from utils.parse.live import LiveParser
from utils.parse.cheese import CheeseParser
from utils.parse.b23 import B23Parser
from utils.parse.festival import FestivalParser
from utils.parse.popular import PopularParser
from utils.parse.space.list import SpaceListParser
from utils.parse.space.space import SpaceParser
from utils.parse.space.favlist import FavListParser
from utils.parse.preview import VideoPreview, PreviewInfo

_ = gettext.gettext

class Parser:
    def __init__(self, parent: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.main_window: MainWindow = parent

    def init_utils(self):
        self.parse_type: ParseType = None

    def get_parse_type(self, url: str):
        for (type, url_pattern) in url_pattern_map:
            if match := Regex.search(url_pattern, url):
                return type

    def get_parser(self, type: str):
        parser_map = {
            "video": (ParseType.Video, VideoParser(self.parser_callback)),
            "bangumi": (ParseType.Bangumi, BangumiParser(self.parser_callback)),
            "cheese": (ParseType.Cheese, CheeseParser(self.parser_callback)),
            "live": (ParseType.Live, LiveParser(self.parser_callback)),
            "space": (ParseType.Space, SpaceParser(self.parser_callback)),
            "space_list": (ParseType.List, SpaceListParser(self.parser_callback)),
            "popular": (ParseType.Popular, PopularParser(self.parser_callback)),
            "favlist": (ParseType.FavList, FavListParser(self.parser_callback)),
            "b23": (ParseType.B23, B23Parser(self.parser_callback)),
            "festival": (ParseType.Festival, FestivalParser(self.parser_callback))
        }

        (self.parse_type, parser) = parser_map.get(type)

        return parser

    def parse_url(self, url: str, set_status: bool = True):
        if set_status:
            self.main_window.utils.set_status(ParseStatus.Parsing)

        new_url = self.validate_url(url)

        type = self.get_parse_type(new_url)

        if not type:
            raise GlobalException(code = StatusCode.URL.value, callback = self.onError, parse_url = url)

        self.parser: VideoParser = self.get_parser(type)

        rtn_val = self.parser.parse_url(new_url)

        if StatusCode(rtn_val) == StatusCode.Success:
            VideoPreview.clear_cache()

            if Config.Basic.enable_history:
                self.main_window.history.add(url)
            
            wx.CallAfter(self.parse_success)
    
    def parse_success(self):
        self.main_window.utils.set_status(ParseStatus.Success)

        if self.parse_type == ParseType.Live:
            wx.CallAfter(self.live_recording)

        else:
            self.parse_type_str = self.parser.get_parse_type_str()

            PreviewInfo.episode_info = self.main_window.episode_list.GetCurrentEpisodeInfo()

            self.main_window.utils.update_history()

            wx.CallAfter(self.main_window.show_episode_list, False)

    def parse_episode(self):
        self.parser.parse_episodes()

    def live_recording(self):
        self.main_window.onShowLiveRecordingWindowEVT(0)

        self.main_window.live_recording_window.add_to_live_list([self.parser.get_live_info()], create_local_file = True)

    def onError(self):
        self.main_window.utils.set_status(ParseStatus.Error)

        show_error_message_dialog(_("解析失败"), parent = self.main_window)

    def onJump(self, url: str):
        Thread(target = self.parse_url, args = (url, False, )).start()

    def validate_url(self, url: str):
        if url.startswith(("BV", "av", "ep", "ss", "md")):
            return url
        
        elif match := Regex.search(r"https?://(([a-z0-9-]+)\.)?(bilibili|b23|bili2233)\.(com|tv|cn)/[\w\?=/._&%-]*", url):
            return match[0]
        
        else:
            return ""

    def refresh_media_info(self, item_info: TreeListItemInfo):
        PreviewInfo.video_size_cache.clear()
        PreviewInfo.audio_size_cache.clear()

        match ParseType(item_info.type):
            case ParseType.Video:
                bvid, cid = item_info.bvid, item_info.cid

                VideoParser.start_thread(VideoParser.get_video_available_media_info, (bvid, cid,))

            case ParseType.Bangumi:
                bvid, cid = item_info.bvid, item_info.cid

                BangumiParser.start_thread(BangumiParser.get_bangumi_available_media_info, (bvid, cid,))

            case ParseType.Cheese:
                aid, ep_id, cid = item_info.aid, item_info.ep_id, item_info.cid

                CheeseParser.start_thread(CheeseParser.get_cheese_available_media_info, (aid, ep_id, cid,))

        PreviewInfo.episode_info = item_info.to_dict()

    @property
    def parser_callback(self):
        class Callback(ParseCallback):
            @staticmethod
            def onError():
                self.onError()
            
            @staticmethod
            def onJump(url: str):
                self.onJump(url)

            @staticmethod
            def onUpdateName(name: str):
                window = wx.FindWindowByName("processing")
                window.UpdateName(name)

            @staticmethod
            def onUpdateTitle(title: str):
                window = wx.FindWindowByName("processing")
                window.UpdateTitle(title)

        return Callback