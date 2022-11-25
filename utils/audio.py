import re
import json
import requests

from .tools import *

class AudioInfo:
    sid = amid = duration = count = 0

    url = title = lyric = ""

    playlist = down_list = []

    isplaylist = False

class AudioParser:
    def __init__(self, onError):
        self.onError = onError

    @property
    def info_api(self):
        return "https://www.bilibili.com/audio/music-service-c/web/song/info?sid={}".format(AudioInfo.sid)

    @property
    def playlist_api(self):
        return "https://www.bilibili.com/audio/music-service-c/web/song/of-menu?sid={}&pn=1&ps=100".format(AudioInfo.amid)

    def get_sid(self, url):
        result = re.findall(r"au[0-9]*", url)
        AudioInfo.sid =  result[len(result) - 1][2:]

        AudioInfo.url = "https://www.bilibili.com/audio/au{}".format(AudioInfo.sid)

    def get_amid(self, url):
        AudioInfo.amid = re.findall(r"am[0-9]*", url)[0][2:]

        AudioInfo.url = "https://www.bilibili.com/audio/am{}".format(AudioInfo.amid)

    def get_audio_info(self):
        audio_request = requests.get(self.info_api, headers = get_header(), proxies = get_proxy())
        audio_json = json.loads(audio_request.text)

        self.check_json(audio_json)

        AudioInfo.title = audio_json["data"]["title"]
        AudioInfo.duration = audio_json["data"]["duration"]
        AudioInfo.lyric = audio_json["data"]["lyric"]
        
        AudioInfo.count = 1
        AudioInfo.isplaylist = False
        AudioInfo.down_list = AudioInfo.playlist = []
    
    def get_playlist_info(self):
        audio_request = requests.get(self.playlist_api, headers = get_header(), proxies = get_proxy())
        audio_json = json.loads(audio_request.text)

        self.check_json(audio_json)

        AudioInfo.count = audio_json["data"]["totalSize"]
        AudioInfo.playlist = audio_json["data"]["data"]

        AudioInfo.isplaylist = True

    def parse_url(self, url):
        if "am" in url:
            self.get_amid(url)

            self.get_playlist_info()
        else:
            self.get_sid(url)

            self.get_audio_info()
    
    def check_json(self, json):  
        if json["code"] != 0 or json["data"] == None:
            self.onError(400)
            