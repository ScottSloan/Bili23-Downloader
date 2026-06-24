from ...common.translator import Translator
from ...common._json import json_dumps

from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

import re

class CheeseEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self):
        self.episode_data_parser()

        node = self.sections_parser()

        if self.target_episode_info:
            return node
        else:
            current_episode_data = ("ep_id", self.get_ep_id()) 

            self.update_episode_list(node, current_episode_data)

    def sections_parser(self):
        cheese_title = self.info_data["title"]
        node_data = {
            "number": Translator.EPISODE_TYPE("COURSE"),
            "title": cheese_title
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        for section in self.info_data["sections"]:
            if section["episodes"]:
                section_title = section["title"]
                section_node_data = {
                    "number": "章节",
                    "title": section_title
                }

                section_node = TreeItem(section_node_data)
                section_node.set_attribute(Attribute.TREE_NODE_BIT)
                
                for episode in section["episodes"]:
                    self.episode_count += 1

                    episode_item_data = {
                        "aid": episode["aid"],
                        "badge": self.get_episode_badge(episode),
                        "cid": episode["cid"],
                        "cover": episode["cover"],
                        "duration": self.get_episode_duration(episode),
                        "ep_id": episode["id"],
                        "episode_id": self.episode_id,
                        "episode_plot": "{} · {}".format(episode["play_way_subtitle"], episode["subtitle"]),
                        "number": self.episode_count,
                        "episode_number": self.episode_count,
                        "pubtime": episode["release_date"],
                        "title": episode["title"],
                        "related_titles": {
                            "series_title": cheese_title,
                            "section_title": section_title
                        },
                        "url": "https://www.bilibili.com/cheese/play/{ep_id}".format(ep_id = episode["id"])
                    }

                    episode_item = TreeItem(episode_item_data)
                    episode_item.set_attribute(Attribute.CHEESE_BIT)

                    if self.target_attribute:
                        episode_item.set_attribute(self.target_attribute)

                    section_node.add_child(episode_item)

                root_node.add_child(section_node)

        return root_node
    
    def episode_data_parser(self):
        episode_data = self._init_episode_data()

        if self.target_episode_data_id:
            data = EpisodeData.get_episode_data(self.target_episode_data_id)

            episode_data.update(data)

        episode_data["poster"] = self.info_data["cover"]
        episode_data["description"] = self.info_data["subtitle"]
        episode_data["styles"] = ["Bilibili 课堂"]
        episode_data["premiered"] = self.get_premiered()
        # season_id
        episode_data["season_id"] = self.info_data["season_id"]
        # 发布者信息
        episode_data["uploader"] = self.info_data["up_info"]["uname"]
        episode_data["uploader_uid"] = self.info_data["up_info"]["mid"]
        episode_data["uploader_face"] = self.info_data["up_info"]["avatar"]

    def get_episode_badge(self, episode_data: dict):
        if "label" in episode_data:
            return episode_data["label"]
        
        return {
            1: "全集试看",
            2: "付费",
            3: "部分试看"
        }.get(episode_data["status"])
    
    def get_premiered(self):
        text = json_dumps(self.info_data)

        # 使用正则找到第一条 release_date 字段对应的值
        match = re.search(r'"release_date"\s*:\s*(\d+)', text)

        if match:
            return int(match.group(1))
        else:
            return 0
        
    def get_ep_id(self):
        # 如果 info_data 中存在 current_ep_id 字段，优先使用该字段作为 ep_id
        if "current_ep_id" in self.info_data:
            return self.info_data.get("current_ep_id")
        
        else:
            # 否则从正片章节中获取第一个剧集的 ep_id 作为 ep_id
            for section in self.info_data["sections"]:
                for episode in section["episodes"]:
                    return episode.get("id", "")
            
            return ""