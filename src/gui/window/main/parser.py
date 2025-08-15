import wx

from utils.config import Config

from utils.common.regex import Regex
from utils.common.enums import ParseType, ParseStatus, ProcessingType, StatusCode
from utils.common.model.callback import ParseCallback
from utils.common.thread import Thread
from utils.common.exception import GlobalException, GlobalExceptionInfo
from utils.common.map import url_pattern_map

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.live import LiveParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.b23 import B23Parser
from utils.parse.festival import FestivalParser
from utils.parse.preview import VideoPreview, PreviewInfo
from utils.parse.popular import PopularParser
from utils.parse.space_list import SpaceListParser
from utils.parse.space import SpaceParser

class Parser:
    def __init__(self, parent: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.main_window: MainWindow = parent
        self.url = None

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
            "b23": (ParseType.B23, B23Parser(self.parser_callback)),
            "festival": (ParseType.Festival, FestivalParser(self.parser_callback))
        }

        (parse_type, parser) = parser_map.get(type)

        self.parse_type = parse_type

        return parser

    def parse_url(self, url: str):
        self.url = url

        type = self.get_parse_type(url)

        if not type:
            raise GlobalException(code = StatusCode.URL.value, callback = self.onError)
            
        self.parser: VideoParser = self.get_parser(type)
    
        rtn_val = self.parser.parse_url(url)

        if StatusCode(rtn_val) == StatusCode.Success:
            wx.CallAfter(self.parse_success)
    
    def parse_success(self):
        self.main_window.utils.set_status(ParseStatus.Success)

        match self.parse_type:
            case ParseType.Live:
                wx.CallAfter(self.live_recording)

            case _:
                self.parse_type_str = self.parser.get_parse_type_str()

                self.main_window.show_episode_list(from_menu = False)

                self.set_video_quality_id()

                self.set_stream_type()

    def set_video_quality_id(self):
        self.video_quality_data_dict = VideoPreview.get_video_quality_data_dict(PreviewInfo.download_json)

        self.video_quality_id =  Config.Download.video_quality_id if Config.Download.video_quality_id in self.video_quality_data_dict.id_list() else max(VideoPreview.get_video_available_quality_id_list(PreviewInfo.download_json))

        self.video_codec_id = Config.Download.video_codec_id

    def set_stream_type(self):
        match self.parse_type:
            case ParseType.Video:
                self.stream_type = VideoInfo.stream_type
            
            case ParseType.Bangumi:
                self.stream_type = BangumiInfo.stream_type
            
            case ParseType.Cheese:
                self.stream_type = CheeseInfo.stream_type

    def parse_episode(self):
        self.parser.parse_episodes()

    def live_recording(self):
        self.main_window.onShowLiveRecordingWindowEVT(0)

        self.main_window.live_recording_window.add_to_live_list([self.parser.get_live_info()], create_local_file = True)

    def onError(self):
        def worker():
            self.main_window.utils.set_status(ParseStatus.Error)

            info = GlobalExceptionInfo.info.copy()

            self.main_window.utils.show_error_message_dialog(f"解析失败\n\n错误码：{info.get('code')}\n描述：{info.get('message')}", "错误", info)

        wx.CallAfter(worker)

    def onJump(self, url: str):
        Thread(target = self.parse_url, args = (url, )).start()

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
            def onChangeProcessingType(type: ProcessingType):
                self.main_window.processing_window.SetType(type)

            @staticmethod
            def onUpdateName(name: str):
                self.main_window.processing_window.UpdateName(name)

            @staticmethod
            def onUpdateTitle(title: str):
                self.main_window.processing_window.UpdateTitle(title)

        return Callback