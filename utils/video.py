import re
import wx
import os
import json
import parsel
import requests
from utils.config import Config

from utils.tools import combine_video_audio, format_data, get_header
from utils.download import Downloader

class VideoInfo:
    url = bvid = cid = ""

    title = desc = cover = ""

    view = like = coin = danmaku = favorite = reply = quality = 0

    pages = down_pages = quality_id = quality_desc =  []

    multiple = False

class VideoParser:
    def aid_api(self, aid: str) -> str:
        return "https://api.bilibili.com/x/web-interface/archive/stat?aid=" + aid

    def info_api(self) -> str:
        return "https://api.bilibili.com/x/web-interface/view?bvid=" + VideoInfo.bvid

    def danmaku_url(self, cid: str):
        return "https://comment.bilibili.com/{}.xml".format(cid)

    def get_aid(self, url: str):
        aid = re.findall(r"av[0-9]*", url)[0][2:]
        aid_request = requests.get(self.aid_api(aid), headers = get_header())
        aid_json = json.loads(aid_request.text)

        if aid_json["code"] != 0:
            wx.CallAfter(self.on_error, 400)

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
            wx.CallAfter(self.on_error, 400)

        info_data = info_json["data"]
        if info_data["tname"] == "连载动画":
            #main_window.get_thread(info_data["redirect_url"])
            return
        
        VideoInfo.title = info_data["title"]
        VideoInfo.desc = info_data["desc"] if info_data["desc"] != "-" else "暂无简介"
        VideoInfo.cover = info_data["pic"]
        VideoInfo.pages = info_data["pages"]
        VideoInfo.cid = info_data["cid"]

        info_stat = info_data["stat"]
        VideoInfo.view = format_data(info_stat["view"])
        VideoInfo.like = format_data(info_stat["like"])
        VideoInfo.coin = format_data(info_stat["coin"])
        VideoInfo.danmaku = format_data(info_stat["danmaku"])
        VideoInfo.favorite = format_data(info_stat["favorite"])
        VideoInfo.reply = format_data(info_stat["reply"])

        from utils.html import save_video_info

        save_video_info()
        
    def get_video_quality(self):
        video_request = requests.get(VideoInfo.url, headers = get_header())
        selector = parsel.Selector(video_request.text)

        video_json = json.loads(selector.css("head > script:nth-child(33) ::text").extract_first()[20:])
        json_data = video_json["data"]

        VideoInfo.quality_id = json_data["accept_quality"]
        VideoInfo.quality_desc = json_data["accept_description"]

    def get_video_durl(self, kwargs):
        self.downloader = Downloader(kwargs["on_start"], kwargs["on_download"])
        on_complete, self.on_combine = kwargs["on_complete"], kwargs["on_combine"]

        if VideoInfo.multiple:
            for index, value in enumerate(VideoInfo.down_pages):
                name = value["part"]
                page = value["page"]
                cid = value["cid"]

                self.process_video_durl(VideoInfo.url + "?p=%d" % page, name, index)
                self.get_video_danmaku(name, cid)
        else:
            self.process_video_durl(VideoInfo.url, VideoInfo.title, 0)
            self.get_video_danmaku(VideoInfo.title, VideoInfo.cid)

        wx.CallAfter(on_complete, "视频下载完成")
        
    def process_video_durl(self, referer_url: str, title: str, index):
        video_request = requests.get(referer_url, headers = get_header())
        selector = parsel.Selector(video_request.text)

        video_json = json.loads(selector.css("head > script:nth-child(33) ::text").extract_first()[20:])
        json_dash = video_json["data"]["dash"]

        video_durl = [i["baseUrl"] for i in json_dash["video"] if i["id"] == VideoInfo.quality][0]
        audio_durl = json_dash["audio"][0]["baseUrl"]

        index = [index + 1, len(VideoInfo.down_pages)]

        self.downloader.add_url(video_durl, referer_url, "video.mp4", index, title)
        self.downloader.add_url(audio_durl, referer_url, "audio.mp3", index, title)

        wx.CallAfter(combine_video_audio, title, self.on_combine)
        
    def get_video_danmaku(self, name: str, cid: str):
        if not Config.save_danmaku:
            return

        req = requests.get(self.danmaku_url(cid), headers = get_header())

        with open(os.path.join(Config.download_path, "{}.xml".format(name)), "w", encoding = "utf-8") as f:
            f.write(req.text)

    def parse_url(self, url: str, on_error):
        self.on_error = on_error

        if "av" in url:
            self.get_aid(url)
        elif "BV" in url:
            self.get_bvid(url)
        
        wx.CallAfter(self.get_video_info)
        wx.CallAfter(self.get_video_quality)
