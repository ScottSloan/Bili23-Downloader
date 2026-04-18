from util.common import Translator
from util.format.time import Time

from .tree import TreeItem, Attribute, EpisodeData
from .base import EpisodeParserBase

class BangumiEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str, kwargs = {}):
        super().__init__(**kwargs)

        self.info_data = info_data["result"]
        self.episode_number_map = {}
        self.category_name = category_name

        self.update_info_data()

    def parse(self):
        self.episode_data_parser()

        node = self.sections_parser()

        if self.target_episode_info:
            return node
        else:
            current_ep_id = self.info_data.get("current_ep_id")

            current_episode_data = ("ep_id", current_ep_id) if current_ep_id else None

            self.update_episode_list(node, current_episode_data)

    def sections_parser(self):
        season_title = self.info_data["season_title"]
        node_data = {
            "number": Translator.EPISODE_TYPE(self.category_name),
            "title": season_title
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        episode_count = 0

        for section in self.info_data["sections"]:
            section_title = section["title"]
            section_node_data = {
                "number": "章节",
                "title": section_title
            }

            section_node = TreeItem(section_node_data)
            section_node.set_attribute(Attribute.TREE_NODE_BIT)

            for episode in section["episodes"]:
                if self.target_episode_info:
                    # 如果指定了目标剧集信息，但当前剧集的 ep_id 不匹配，则跳过该剧集
                    if episode.get("ep_id") != self.target_episode_info:
                        continue

                episode_count += 1

                episode_item_data = {
                    "aid": episode["aid"],
                    "episode_id": self.episode_id,
                    "episode_number": self.episode_number_map.get(episode["cid"], 0),
                    "badge": episode["badge"],
                    "bvid": episode.get("bvid"),
                    "cid": episode["cid"],
                    "cover": episode["cover"],
                    "duration": int(self.get_episode_duration(episode) / 1000),
                    "ep_id": episode["ep_id"],
                    "number": episode_count,
                    "pubtime": episode["pub_time"],
                    "title": self.get_bangumi_title(episode),
                    "related_titles": {
                        "season_title": season_title,
                        "section_title": section_title
                    },
                    "episode_plot": "《{season_title}》{episode_title}".format(season_title = season_title, episode_title = self.get_bangumi_title(episode)),
                    "url": episode["link"]
                }

                episode_item = TreeItem(episode_item_data)
                episode_item.set_attribute(Attribute.BANGUMI_BIT)

                if self.target_attribute:
                    episode_item.set_attribute(self.target_attribute)

                section_node.add_child(episode_item)

            root_node.add_child(section_node)

        return root_node

    def update_info_data(self):
        self.info_data["sections"] = [
            {
                "title": "正片",
                "episodes": self.info_data["episodes"]
            }
        ]

        section = self.info_data.get("section")

        if section:
            self.info_data["sections"].extend(section)

        # 未登录时，预告片会与正片混合，导致剧集序号错误；登录后，预告片会被单独分到一个章节中，不会影响正片的剧集序号
        # 因此，此处过滤未登录时正片中混杂的预告片，用于准确获取剧集序号
        episode_number = 0

        for episode in self.info_data["episodes"]:
            if episode["badge"] != "预告":
                episode_number += 1

                self.episode_number_map[episode["cid"]] = episode_number

        # 所谓 “UP主陪你看” 章节，是没有 bvid 和 cid 的，属于投稿视频，不在剧集范围内，故剔除
        self.info_data["sections"] = [
            section for section in self.info_data["sections"]
            if all("bvid" in episode and "cid" in episode for episode in section["episodes"])
        ]

    def episode_data_parser(self):
        self.episode_id = EpisodeData.add_episode()
        episode_data = EpisodeData.get_episode_data(self.episode_id)

        if self.target_episode_data_id:
            data = EpisodeData.get_episode_data(self.target_episode_data_id)

            episode_data.update(data)

        # 系列标题
        episode_data["series_title"] = self.info_data["series"]["series_title"]
        # season_id 和 media_id
        episode_data["season_id"] = self.info_data["season_id"]
        episode_data["media_id"] = self.info_data["media_id"]
        # season_number
        episode_data["season_number"] = self.determine_season_number()

        # 地区
        episode_data["areas"] = [entry["name"] for entry in self.info_data.get("areas", "")]
        # 发行日期
        episode_data["premiered"] = int(Time.from_string(self.info_data["publish"]["pub_time"]).timestamp())
        # 简介
        episode_data["description"] = self.info_data.get("evaluate", "")
        # 风格
        episode_data["styles"] = self.info_data.get("styles", "") + ["Bilibili {category_name}".format(category_name = Translator.EPISODE_TYPE(self.category_name))]
        # 海报
        episode_data["poster"] = self.info_data.get("cover", "")
        # 演员
        episode_data["actors"] = self.info_data.get("actors", "")
        # 评分
        if self.info_data.get("rating"):
            episode_data["rating"] = self.info_data["rating"]["score"]

        if self.info_data.get("up_info"):
            episode_data["uploader"] = self.info_data["up_info"]["uname"]
            episode_data["uploader_uid"] = self.info_data["up_info"]["mid"]

    def determine_season_number(self):
        season_id = self.info_data["season_id"]

        for index, entry in enumerate(self.info_data["seasons"]):
            if entry["season_id"] == season_id:
                return index + 1

    def get_bangumi_title(self, episode_data: dict):
        show_title = episode_data.get("show_title")

        if show_title:
            return show_title
        
        else:
            return episode_data.get("title", "")
