import re
import json
import requests

from utils.tools import get_header, get_proxy

class AudioInfo:
    sid = uid = duration = 0

    title = intro = author = lyric = ""

class AudioParser:
    def info_api(self) -> str:
        return "https://www.bilibili.com/audio/music-service-c/web/song/info?sid={}".format(AudioInfo.sid)

    def get_sid(self, url: str):
        AudioInfo.sid =  re.findall(r"audio/au[0-9]*", url)[0][8:]

    def get_audio_info(self):
        audio_request = requests.get(self.info_api(), headers = get_header(), proxies = get_proxy())
        audio_json = json.loads(audio_request.text)

        AudioInfo.uid = audio_json["data"]["uid"]
        AudioInfo.title = audio_json["data"]["title"]
        AudioInfo.intro = audio_json["data"]["intro"]
        AudioInfo.duration = audio_json["data"]["duration"]
        AudioInfo.lyric = audio_json["data"]["lyric"]
        
    def parse_url(self, url: str):
        self.get_sid(url)

        self.get_audio_info()