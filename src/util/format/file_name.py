from util.parse.episode.tree import Attribute
from util.common.enum import ConventionType
from util.common import config
from util.format.time import Time

from ..download.task.info import TaskInfo

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

class FileNameFormatter:
    def __init__(self):
        self.type_id = None
        self.rule = None
        self.variable_data: dict = {}

        self.attribute = None

    def set_type_id(self, type_id: int):
        self.type_id = type_id

    def set_rule(self, rule: str):
        self.rule = rule

    def set_variable_data(self, data: TaskInfo | List[dict]):
        if isinstance(data, TaskInfo):
            self.variable_data = self.get_variable_data_from_task_info(data)

            self.type_id = self.get_type_id_from_task_info(data)

        elif isinstance(data, list):
            for entry in data:
                name = entry.get("name")
                example = entry.get("example")

                if name in ["pub_time", "create_time"]:
                    example = Time.from_timestamp(1772841600)

                self.variable_data[name] = example

    def format(self):
        try:
            if not self.rule:
                self.rule = self.get_rule_from_config(self.type_id)

            if self.attribute:
                self.rule = self.get_special_rule()

            return self.rule.format(**self.variable_data)
        
        except Exception as e:
            logger.exception(f"格式化文件名时发生错误")

            return None

    def get_special_rule(self):
        # 判断是否为特殊类型的视频：互动视频、每周必看、收藏夹、个人空间
        # 这些类型不支持自定义，直接使用内部预设规则

        rule_map = {
            Attribute.DOWNLOAD_AS_SINGLE_VIDEO_BIT: "{leaf_title}",
            Attribute.INTERACTIVE_BIT: "{collection_title}/{leaf_title}",
            Attribute.POPULAR_BIT: "{collection_title}/{leaf_title}",
            Attribute.COLLECTION_LIST_BIT: "{collection_title}/{leaf_title}",
            Attribute.FAVLIST_BIT: Path("{favorites_owner_id}_{favorites_owner}") / self.rule,
            Attribute.SPACE_BIT: Path("{space_owner_id}_{space_owner}") / self.rule,
            Attribute.WATCH_LATER_BIT: "{leaf_title}"
        }

        for attr, rule in rule_map.items():
            if self.attribute & attr:
                return str(Path(rule))
        
        return self.rule
        
    def get_rule_from_config(self, type_id: int = None):
        # 从命名规则配置中查询到对应的命名规则模板
        for entry in config.get(config.naming_rule_list):
            if entry["type"] == type_id and entry["default"]:
                return entry["rule"]

    def get_rule_by_id(self, rule_id: int):
        for entry in config.get(config.naming_rule_list):
            if entry["id"] == rule_id:
                return entry["rule"]

    def get_variable_data_from_task_info(self, task_info: TaskInfo):
        return {
            "pub_time": Time.from_timestamp(task_info.Episode.pubtime),
            "pub_ts": task_info.Episode.pubtime,
            "create_time": Time.from_timestamp(task_info.Basic.created_time),
            "create_ts": task_info.Basic.created_time,
            "number": task_info.Episode.number,
            "uploader": task_info.Episode.uploader,
            "uploader_uid": task_info.Episode.uploader_uid,
            "video_quality": task_info.Episode.video_quality,
            "audio_quality": task_info.Episode.audio_quality,
            "video_codec": task_info.Episode.video_codec,

            "aid": task_info.Episode.aid,
            "bvid": task_info.Episode.bvid,
            "cid": task_info.Episode.cid,
            "ep_id": task_info.Episode.ep_id,
            "season_id": task_info.Episode.season_id,

            "leaf_title": task_info.Episode.leaf_title,
            "parent_title": task_info.Episode.parent_title,
            "section_title": task_info.Episode.section_title,
            "collection_title": task_info.Episode.collection_title,
            "series_title": task_info.Episode.series_title,
            "season_title": task_info.Episode.season_title,
            "episode_title": task_info.Episode.episode_title,

            "season_number": task_info.Episode.season_number,
            "episode_number": task_info.Episode.episode_number,
            "p": task_info.Episode.part_number,

            "favorites_name": task_info.Episode.favorites_name,
            "favorites_id": task_info.Episode.favorites_id,
            "favorites_owner":task_info.Episode.favorites_owner,
            "favorites_owner_id": task_info.Episode.favorites_owner_id,
            "space_owner": task_info.Episode.space_owner,
            "space_owner_id": task_info.Episode.space_owner_id
        }
    
    def get_type_id_from_task_info(self, task_info: TaskInfo):
        self.attribute = task_info.Episode.attribute

        return self.get_type_id_from_attribute(task_info.Episode.attribute)

    def get_type_id_from_attribute(self, attribute: int):
        type_map = {
            Attribute.NORMAL_BIT: ConventionType.NORMAL,
            Attribute.PART_BIT: ConventionType.PART,
            Attribute.COLLECTION_BIT: ConventionType.COLLECTION,
            Attribute.BANGUMI_BIT: ConventionType.BANGUMI,
            Attribute.CHEESE_BIT: ConventionType.CHEESE,
            Attribute.POPULAR_BIT: ConventionType.NORMAL
        }

        for attr, type_id in type_map.items():
            if attribute & attr != 0:
                return type_id

    def get_rule_list_from_attribute(self, attribute: int):
        type_id = self.get_type_id_from_attribute(attribute)

        rule_list = []

        for entry in config.get(config.naming_rule_list):
            if entry["type"] == type_id:
                rule_list.append(entry)

        return rule_list
    