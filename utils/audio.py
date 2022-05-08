import re
import json
import requests

from utils.tools import get_header, get_proxy

class AudioInfo:
    sid = uid = amid = duration = count = 0

    title = intro = author = lyric = ""
    
    playlist = down_list = []

    isplaylist = False

class AudioParser:
    @property
    def info_api(self) -> str:
        return "https://www.bilibili.com/audio/music-service-c/web/song/info?sid={}".format(AudioInfo.sid)

    @property
    def playlist_api(self) -> str:
        return "https://www.bilibili.com/audio/music-service-c/web/song/of-menu?sid={}&pn=1&ps=100".format(AudioInfo.amid)

    def get_sid(self, url: str):
        result = re.findall(r"au[0-9]*", url)
        AudioInfo.sid = result[len(result) - 1][2:]

    def get_amid(self, url: str):
        AudioInfo.amid =  re.findall(r"am[0-9]*", url)[0][2:]

    def get_audio_info(self):
        audio_request = requests.get(self.info_api, headers = get_header(), proxies = get_proxy())
        audio_json = json.loads(audio_request.text)

        if audio_json["code"] != 0:
            self.on_error(400)
            return

        audio_data = audio_json["data"]

        AudioInfo.uid = audio_data["uid"]
        AudioInfo.title = audio_data["title"]
        AudioInfo.intro = audio_data["intro"]
        AudioInfo.duration = audio_data["duration"]
        AudioInfo.lyric = audio_data["lyric"]

        AudioInfo.isplaylist = False
        AudioInfo.playlist = []

    def get_audio_playlist(self):
        audio_request = requests.get(self.playlist_api, headers = get_header(), proxies = get_proxy())
        audio_json = json.loads(audio_request.text)

        if audio_json["code"] != 0:
            self.on_error(400)
            return
        
        audio_data = audio_json["data"]

        AudioInfo.count = audio_data["totalSize"]
        AudioInfo.playlist = audio_data["data"]

        AudioInfo.isplaylist = True

    def parse_url(self, url: str, on_error):
        self.on_error = on_error

        if "am" in url:
            self.get_amid(url)

            self.get_audio_playlist()
        else:
            self.get_sid(url)

            self.get_audio_info()