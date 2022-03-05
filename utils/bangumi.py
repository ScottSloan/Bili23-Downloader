import re
import wx
import os
import json
import parsel
import requests

from utils.config import Config
from utils.tools import combine_video_audio, format_data, get_header
from utils.download import Downloader

class BangumiInfo:
    url = epid = bvid = ""
    
    title = desc = cover = newep = theme = ""

    view = coin = danmaku = favorite = score = count = quality = 0

    episodes = down_episodes = quality_id = quality_desc = []

    sections = {}

class BangumiParser:
    def media_api(self, media_id: str):
        return "https://api.bilibili.com/pgc/review/user?media_id=" + media_id

    def season_api(self, season_id: str):
        return "https://api.bilibili.com/pgc/web/season/section?season_id=" + season_id

    def info_api(self):
        return "https://api.bilibili.com/pgc/view/web/season?ep_id=" + BangumiInfo.epid

    def danmaku_url(self, cid: str):
        return "https://comment.bilibili.com/{}.xml".format(cid)

    def get_epid(self, url: str):
        epid = re.findall(r"ep[0-9]*", url)[0][2:]
        self.set_epid(epid)

    def get_season_id(self, url: str):
        season_id = re.findall(r"ss[0-9]*", url)[0][2:]
        season_request = requests.get(self.season_api(season_id), headers = get_header())
        season_json = json.loads(season_request.text)

        if season_json["code"] != 0:
            wx.CallAfter(self.on_error, 400)

        epid = str(season_json["result"]["main_section"]["episodes"][0]["id"])
        self.set_epid(epid)

    def get_media_id(self, url: str):
        media_id = re.findall(r"md[0-9]*", url)[0][2:]
        media_request = requests.get(self.media_api(media_id), headers = get_header())
        media_json = json.loads(media_request.text)

        if media_json["code"] != 0:
            wx.CallAfter(self.on_error, 400)

        season_id = media_json["result"]["media"]["season_id"]
        self.get_season_id("ss" + str(season_id))

    def set_epid(self, epid: str):
        BangumiInfo.epid, BangumiInfo.url = epid, "https://www.bilibili.com/bangumi/play/ep" + epid

    def get_bangumi_info(self):
        info_request = requests.get(self.info_api(), headers = get_header())
        info_json = json.loads(info_request.text)

        if info_json["code"] != 0:
            wx.CallAfter(self.on_error, 400)
        
        info_result = info_json["result"]
        BangumiInfo.url = info_result["episodes"][0]["link"]
        BangumiInfo.title = info_result["title"]
        BangumiInfo.cover = info_result["cover"]
        BangumiInfo.desc = info_result["evaluate"]
        BangumiInfo.newep = info_result["new_ep"]["desc"]
        BangumiInfo.theme = info_result["up_info"]["uname"][4:]

        if "rating" in info_result:
            BangumiInfo.count = str(info_result["rating"]["count"])
            BangumiInfo.score = str(info_result["rating"]["score"])

        BangumiInfo.episodes = info_result["episodes"]
        BangumiInfo.sections["正片"] = BangumiInfo.episodes

        if "section" in info_result and Config.show_sections:
            info_section = info_result["section"]

            for section in info_section:
                section_title = section["title"]
                section_episodes = section["episodes"]

                for index, value in enumerate(section_episodes):
                    value["title"] = str(index + 1)

                BangumiInfo.sections[section_title] = section_episodes

        BangumiInfo.url = BangumiInfo.episodes[0]["link"]
        BangumiInfo.bvid = BangumiInfo.episodes[0]["bvid"]

        info_stat = info_result["stat"]
        BangumiInfo.view = format_data(info_stat["views"])
        BangumiInfo.coin = format_data(info_stat["coins"])
        BangumiInfo.danmaku = format_data(info_stat["danmakus"])
        BangumiInfo.favorite = format_data(info_stat["favorites"])
        
        from utils.html import save_bangumi_info

        save_bangumi_info()

    def get_bangumi_quality(self):
        bangumi_request = requests.get(BangumiInfo.url, headers = get_header(cookie = Config.cookie_sessdata))
        selector = parsel.Selector(bangumi_request.text)

        try:
            nth_child = 6 if BangumiInfo.theme != "纪录片" else 7
            bangumi_json = json.loads(selector.css("body > script:nth-child({}) ::text".format(nth_child)).extract_first()[20:])
            json_data = bangumi_json["data"]
            
        except:
            wx.CallAfter(self.on_error)

        BangumiInfo.quality_id = json_data["accept_quality"]
        BangumiInfo.quality_desc = json_data["accept_description"]

    def get_bangumi_durl(self, kwargs):
        self.downloader = Downloader(kwargs["on_start"], kwargs["on_download"])
        on_complete, self.on_combine = kwargs["on_complete"], kwargs["on_combine"]

        for index, value in enumerate(BangumiInfo.down_episodes):
            url = value["link"]
            name = value["share_copy"]
            cid = value["cid"]

            if value["badge"] == "会员" and Config.cookie_sessdata == "":
                continue

            self.process_bangumi_durl(url, name, index)
            self.get_bangumi_danmaku(name, str(cid))


        wx.CallAfter(on_complete, "番剧下载完成")

    def process_bangumi_durl(self, referer_url: str, title: str, index):
        bangumi_request = requests.get(referer_url, headers = get_header(cookie = Config.cookie_sessdata))
        selector = parsel.Selector(bangumi_request.text)

        bangumi_json = json.loads(selector.css("body > script:nth-child(6) ::text").extract_first()[20:])
        json_dash = bangumi_json["data"]["dash"]

        video_durl = [i["baseUrl"] for i in json_dash["video"] if i["id"] == BangumiInfo.quality][0]
        audio_durl = json_dash["audio"][0]["baseUrl"]

        index = [index + 1, len(BangumiInfo.down_episodes)]

        self.downloader.add_url(video_durl, referer_url, "video.mp4", index, title)
        self.downloader.add_url(audio_durl, referer_url, "audio.mp3", index, title)
        
        wx.CallAfter(combine_video_audio, title, self.on_combine)

    def get_bangumi_danmaku(self, name: str, cid: str):
        if not Config.save_danmaku:
            return

        req = requests.get(self.danmaku_url(cid), headers = get_header())
        
        with open(os.path.join(os.getcwd(), "{}.xml".format(name)), "w", encoding = "utf-8") as f:
            f.write(req.text)

    def parse_url(self, url: str, on_error):
        self.on_error = on_error

        if "ep" in url:
            self.get_epid(url)
        elif "ss" in url:
            self.get_season_id(url)
        elif "md" in url:
            self.get_media_id(url)
        
        wx.CallAfter(self.get_bangumi_info)
        wx.CallAfter(self.get_bangumi_quality)