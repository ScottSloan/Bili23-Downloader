import re
import wx
import json
import parsel
import requests
from utils.config import Config

from utils.tools import merge_video_audio, format_data, get_header, get_danmaku_subtitle, get_legal_name
from utils.download import Downloader
from utils.error import ProcessError

class VideoInfo:
    url = bvid = cid = ""

    title = desc = cover = ""

    view = like = coin = danmaku = favorite = reply = quality = 0

    pages = episodes = down_pages = quality_id = quality_desc = []

    multiple = collection = False

class VideoParser:
    def aid_api(self, aid: str) -> str:
        return "https://api.bilibili.com/x/web-interface/archive/stat?aid=" + aid

    def info_api(self) -> str:
        return "https://api.bilibili.com/x/web-interface/view?bvid=" + VideoInfo.bvid

    def get_aid(self, url: str):
        aid = re.findall(r"av[0-9]*", url)[0][2:]
        aid_request = requests.get(self.aid_api(aid), headers = get_header())
        aid_json = json.loads(aid_request.text)

        if aid_json["code"] != 0:
            self.on_error(400)

        bvid = aid_json["data"]["bvid"]
        self.set_bvid(bvid)

    def get_bvid(self, url: str):
        bvid = re.findall(r"BV\w*", url)[0]
        self.set_bvid(bvid)

    def set_bvid(self, bvid: str):
        VideoInfo.bvid, VideoInfo.url = bvid, "https://www.bilibili.com/video/" + bvid

    def get_video_info(self):
        info_request = requests.get(self.info_api(), headers = get_header())
        info_json = json.loads(info_request.text)

        if info_json["code"] != 0:
            self.on_error(400)

        info_data = info_json["data"]

        if "redirect_url" in info_data:
            self.on_redirect(info_data["redirect_url"])
            raise ProcessError("Bangumi type detect")
        
        VideoInfo.title = info_data["title"]
        VideoInfo.desc = info_data["desc"] if info_data["desc"] != "-" else "暂无简介"
        VideoInfo.cover = info_data["pic"]
        VideoInfo.pages = info_data["pages"]

        if "ugc_season" in info_data:
            VideoInfo.collection = True

            info_ugc_season = info_data["ugc_season"]
            VideoInfo.title = info_ugc_season["title"]

            VideoInfo.episodes = info_ugc_season["sections"][0]["episodes"]

        VideoInfo.cid = info_data["cid"]

        info_stat = info_data["stat"]
        VideoInfo.view = format_data(info_stat["view"])
        VideoInfo.like = format_data(info_stat["like"])
        VideoInfo.coin = format_data(info_stat["coin"])
        VideoInfo.danmaku = format_data(info_stat["danmaku"])
        VideoInfo.favorite = format_data(info_stat["favorite"])
        VideoInfo.reply = format_data(info_stat["reply"])
        
    def get_video_quality(self):
        video_request = requests.get(VideoInfo.url, headers = get_header(cookie = Config.cookie_sessdata))
        selector = parsel.Selector(video_request.text)

        try:
            video_json = json.loads(selector.css("head > script:nth-child(33) ::text").extract_first()[20:])
        except:
            self.on_error(404)

        json_data = video_json["data"]

        VideoInfo.quality_id = json_data["accept_quality"]
        VideoInfo.quality_desc = json_data["accept_description"]

        from utils.html import save_video_info

        save_video_info()
        
    def get_video_durl(self, kwargs):
        self.downloader = Downloader(kwargs["on_start"], kwargs["on_download"])
        on_complete, self.on_merge = kwargs["on_complete"], kwargs["on_merge"]

        if VideoInfo.multiple:
            for index, value in enumerate(VideoInfo.down_pages):
                name = value["part"]
                page = value["page"]
                cid = value["cid"]

                get_danmaku_subtitle(name, cid, VideoInfo.bvid)
                self.process_video_durl(VideoInfo.url + "?p={}".format(page), name, index)

        elif VideoInfo.collection:
            for index, value in enumerate(VideoInfo.down_pages):
                name = value["title"]
                bvid = value["bvid"]
                url = self.get_full_url(bvid)
                cid = value["cid"]

                get_danmaku_subtitle(name, cid, bvid)
                self.process_video_durl(url, name, index)

        else:
            get_danmaku_subtitle(VideoInfo.title, VideoInfo.cid, VideoInfo.bvid)
            self.process_video_durl(VideoInfo.url, VideoInfo.title, 0)

        wx.CallAfter(on_complete)
        
    def process_video_durl(self, referer_url: str, title: str, index):
        video_request = requests.get(referer_url, headers = get_header(cookie = Config.cookie_sessdata))
        selector = parsel.Selector(video_request.text)

        video_json = json.loads(selector.css("head > script:nth-child(33) ::text").extract_first()[20:])

        index = [index + 1, len(VideoInfo.down_pages)]

        if "dash" in video_json["data"]:
            json_dash = video_json["data"]["dash"]

            quality = json_dash["video"][0]["id"] if json_dash["video"][0]["id"] < VideoInfo.quality else VideoInfo.quality

            video_durl = [i["baseUrl"] for i in json_dash["video"] if i["id"] == quality][0]
            audio_durl = json_dash["audio"][0]["baseUrl"]

            self.downloader.add_url(video_durl, referer_url, "video.mp4", index, title)
            self.downloader.add_url(audio_durl, referer_url, "audio.mp3", index, title)

            merge_video_audio(title, self.on_merge)

        else:
            video_durl = video_json["data"]["durl"][0]["url"]

            self.downloader.add_url(video_durl, referer_url, "{}.mp4".format(get_legal_name(title)), index, title)

    def parse_url(self, url: str, on_redirect, on_error):
        self.on_redirect, self.on_error = on_redirect, on_error

        if "av" in url:
            self.get_aid(url)
        elif "BV" in url:
            self.get_bvid(url)
        
        self.get_video_info()
        self.get_video_quality()

    def get_full_url(self, bvid: str):
        return "https://www.bilibili.com/video/" + bvid
