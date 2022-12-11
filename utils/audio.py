import re
import json
import requests

from .tools import *
from .api import API

class AudioInfo:
    sid = amid = duration = count = 0

    url = title = lyric = ""

    playlist = down_list = []

    isplaylist = False

class AudioParser:
    def __init__(self, onError):
        self.onError = onError

    def get_sid(self, url):
        try:
            AudioInfo.sid = re.findall(r"au([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

        AudioInfo.url = API.Audio.sid_url_api(AudioInfo.sid)

    def get_amid(self, url):
        try:
            AudioInfo.amid = re.findall(r"am([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

        AudioInfo.url = API.Audio.amid_url_api(AudioInfo.amid)

    def get_audio_info(self):
        url = API.Audio.music_info_api(AudioInfo.sid)

        audio_request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        audio_json = json.loads(audio_request.text)

        if self.check_json(audio_json): return

        AudioInfo.title = audio_json["data"]["title"]
        AudioInfo.duration = audio_json["data"]["duration"]
        AudioInfo.lyric = audio_json["data"]["lyric"]
        
        AudioInfo.count = 1
        AudioInfo.isplaylist = False
        AudioInfo.down_list = AudioInfo.playlist = []
    
    def get_playlist_info(self):
        url = API.Audio.playlist_info_api(AudioInfo.amid)

        audio_request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        audio_json = json.loads(audio_request.text)

        if self.check_json(audio_json): return

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
            return True
            