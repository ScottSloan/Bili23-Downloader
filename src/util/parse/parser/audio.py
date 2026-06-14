from ...network.request import SyncNetWorkRequest
from ...common.enum import ParserType

from ..episode.audio import AudioEpisodeParser
from .base import ParserBase

from urllib.parse import urlencode

class AudioParser(ParserBase):
    def __init__(self):
        super().__init__()

    def get_audio_sid(self):
        sid = self.find_str(r"au([0-9]+)", self.url)

        return int(sid)
    
    def get_audio_menu_sid(self):
        sid = self.find_str(r"am([0-9]+)", self.url)

        return int(sid)

    def parse(self, url: str, pn: int = 1):
        self.url = url.replace("audio", "")

        match self.find_str(r"am|au", self.url):
            case "am":
                sid = self.get_audio_menu_sid()

                self.get_audio_menu_info(sid)

            case "au":
                sid = self.get_audio_sid()

                self.get_audio_info(sid)

        episode_parser = AudioEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def get_audio_info(self, sid: int):
        params = {
            "sid": sid
        }

        url = f"https://www.bilibili.com/audio/music-service-c/web/song/info?{urlencode(params)}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_audio_menu_info(self, sid: int):
        params = {
            "sid": sid,
            "pn": 1,
            "ps": 100,
        }

        url = f"https://www.bilibili.com/audio/music-service-c/web/song/of-menu?{urlencode(params)}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_parser_type(self):
        return ParserType.AUDIO