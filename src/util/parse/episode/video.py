from util.common.data import badge_map
from util.common import Translator

from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

class VideoEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self):
        self.episode_data_parser()

        match self.info_data:
            case {"ugc_season": ugc_season} if ugc_season is not None:
                node = self.ugc_season_parser()

            case {"pages": pages} if len(pages) > 1:
                node = self.pages_parser()

            case _:
                node = self.single_parser()

        if self.target_episode_info:
            return node
        else:
            episode_data = ("cid", self.info_data["cid"])
            
            self.update_episode_list(node, episode_data)

    def single_parser(self):
        # 单个视频
        node_data = {
            "number": Translator.EPISODE_TYPE("USER_UPLOADS"),
            "title": ""
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        item_data = {
            "episode_id": self.episode_id,
            "aid": self.info_data["aid"],
            "badge": "充电专属" if self.info_data["is_upower_exclusive"] else "",
            "bvid": self.info_data["bvid"],
            "cid": self.info_data["cid"],
            "cover": self.info_data["pic"],
            "duration": self.get_episode_duration(self.info_data),
            "number": 1,
            "pubtime": self.info_data["pubdate"],
            "title": self.info_data["title"],
            "url": "https://www.bilibili.com/video/{bvid}".format(bvid = self.info_data["bvid"])
        }

        item = TreeItem(item_data)
        self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)

        root_node.add_child(item)

        return root_node

    def pages_parser(self):
        # 分P视频
        parent_title = self.info_data["title"]
        root_node_data = {
            "number": "分P",
            "title": parent_title
        }
        
        root_node = TreeItem(root_node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        for page in self.info_data["pages"]:
            item_data = {
                "aid": self.info_data["aid"],
                "episode_id": self.episode_id,
                "badge": "充电专属" if self.info_data["is_upower_exclusive"] else "",
                "bvid": self.info_data["bvid"],
                "cid": page["cid"],
                "cover": self.info_data["pic"],
                "duration": self.get_episode_duration(page),
                "number": page["page"],
                "pubtime": page["ctime"],
                "part_number": page["page"],
                "title": page["part"],
                "related_titles": {
                    "parent_title": parent_title
                },
                "url": "https://www.bilibili.com/video/{bvid}?p={page}".format(bvid = self.info_data["bvid"], page = page["page"])
            }

            item = TreeItem(item_data)
            self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.PART_BIT)

            root_node.add_child(item)

        return root_node

    def ugc_season_parser(self):
        # 合集
        collection_title = self.info_data["ugc_season"]["title"]
        root_node_data = {
            "number": "合集",
            "title": collection_title
        }

        root_node = TreeItem(root_node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        sections = self.info_data["ugc_season"]["sections"]

        episode_count = 0
        section_count = len(sections)    # 统计章节数量

        for section in sections:
            # 章节
            section_title = section["title"]
            section_data = {
                "number": "章节",
                "title": section_title
            }

            section_node = TreeItem(section_data)
            section_node.set_attribute(Attribute.TREE_NODE_BIT)

            for episode in section["episodes"]:
                if self.target_episode_info:
                    # 如果指定了目标剧集信息，但当前剧集的 cid 不匹配，则跳过该剧集
                    if episode["bvid"] != self.target_episode_info:
                        continue

                if len(episode["pages"]) > 1:
                    parent_title = episode["title"]
                    page_node_data = {
                        "number": "分P",
                        "title": parent_title
                    }

                    page_node = TreeItem(page_node_data)
                    page_node.set_attribute(Attribute.TREE_NODE_BIT)

                    for page in episode["pages"]:
                        episode_count += 1

                        item_data = {
                            "episode_id": self.episode_id,
                            "aid": episode["aid"],
                            "badge": self.get_episode_badge(episode),
                            "bvid": episode["bvid"],
                            "cid": page["cid"],
                            "cover": episode["arc"]["pic"],
                            "duration": self.get_episode_duration(page),
                            "number": episode_count,
                            "pubtime": episode["arc"]["pubdate"],
                            "part_number": page["page"],
                            "title": page["part"],
                            "related_titles": {
                                "collection_title": collection_title,
                                "section_title": section_title if section_count > 1 else "",
                                "parent_title": parent_title
                            },
                            "url": "https://www.bilibili.com/video/{bvid}?p={page}".format(bvid = episode["bvid"], page = page["page"])
                        }

                        item = TreeItem(item_data)
                        self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.COLLECTION_BIT)

                        page_node.add_child(item)

                    if section_count > 1:
                        section_node.add_child(page_node)
                    else:
                        # 如果只有一个正片章节，则不显示"章节"层级，直接添加到根节点
                        root_node.add_child(page_node)

                else:
                    episode_count += 1

                    item_data = {
                        "episode_id": self.episode_id,
                        "aid": episode["aid"],
                        "badge": self.get_episode_badge(episode),
                        "bvid": episode["bvid"],
                        "cid": episode["cid"],
                        "cover": episode["arc"]["pic"],
                        "duration": self.get_episode_duration(episode),
                        "number": episode_count,
                        "pubtime": episode["arc"]["pubdate"],
                        "title": episode["title"],
                        "related_titles": {
                            "collection_title": collection_title,
                            "section_title": section_title if section_count > 1 else ""
                        },
                        "url": "https://www.bilibili.com/video/{bvid}".format(bvid = episode["bvid"])
                    }

                    item = TreeItem(item_data)
                    self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.COLLECTION_BIT)

                    if section_count > 1:
                        section_node.add_child(item)
                    else:
                        # 如果只有一个正片章节，则不显示"章节"层级，直接添加到根节点
                        root_node.add_child(item)

            if section_count > 1:
                root_node.add_child(section_node)

        return root_node

    def episode_data_parser(self):
        # 创建 episode_id
        self.episode_id = EpisodeData.add_episode()
        episode_data = EpisodeData.get_episode_data(self.episode_id)

        if self.target_episode_data_id:
            data = EpisodeData.get_episode_data(self.target_episode_data_id)

            episode_data.update(data)

        # 简介
        episode_data["description"] = self.info_data.get("desc", "")
        # 分区信息
        episode_data["tid"] = self.info_data.get("tid", 0)
        episode_data["tid_v2"] = self.info_data.get("tid_v2", 0)
        # UP 主信息
        episode_data["uploader"] = self.info_data["owner"]["name"]
        episode_data["uploader_uid"] = self.info_data["owner"]["mid"]

    def get_episode_badge(self, episode_data: dict):
        attribute = episode_data.get("attribute", 0)

        for i in badge_map.keys():
            if attribute & (1 << i):
                return badge_map.get(i, "")
        
        return ""
    
    def set_attribute(self, item: TreeItem, attribute: int):
        if self.target_attribute:
            item.set_attribute(self.target_attribute)

        item.set_attribute(attribute)
