import random
from typing import Callable

from utils.config import Config

from utils.common.enums import EpisodeDisplayType

class EpisodeInfo:
    data: dict = {}
    filted_data: dict = {}

    pid_list: list = []
    root_pid: int = 0

    parser = None

    @classmethod
    def get_pid(cls):
        while True:
            pid = random.randint(1, 99999999)

            if pid not in cls.pid_list:
                cls.pid_list.append(pid)
                return pid
            
    @classmethod
    def clear_episode_data(cls, title: str = "视频"):
        cls.root_pid = cls.get_pid()

        cls.pid_list = [cls.root_pid]

        cls.data = {
            "label": title,
            "title": "",
            "pid": cls.root_pid,
            "entries": []
        }
    
    @classmethod
    def clear_filter_data(cls, title: str = "视频"):
        cls.filted_data = {
            "label": title,
            "title": "",
            "pid": cls.root_pid,
            "entries": []
        }

    @classmethod
    def add_item(cls, pid: int, entry_data: dict, target_data: dict = None):
        def add(data: list | dict):
            if isinstance(data, dict):
                if data["pid"] == pid:
                    if "entries" in data:
                        data["entries"].append(entry_data)
                else:
                    if "entries" in data:
                        add(data["entries"])

            elif isinstance(data, list):
                for entry in data:
                    add(entry)

        if not target_data:
            target_data = EpisodeInfo.data

        add(target_data)
        
        return entry_data.get("pid", 0)
        
    @classmethod
    def get_node_info(cls, title: str, duration: int = 0, label: str = ""):
        return {
            "label": label,
            "title": title,
            "duration": duration,
            "pid": cls.get_pid(),
            "entries": [],
            "item_type": "node"
        }

    @staticmethod
    def get_entry_info(episode: dict):
        return {
            "number": 0,
            "page": page if (page := episode.get("page", 0)) and str(page).isnumeric() else 0,
            "season_num": episode.get("season_num", 0),
            "episode_num": episode.get("episode_num", 0),
            "title": episode.get("title", ""),
            "cid": episode.get("cid", 0),
            "aid": episode.get("aid", 0),
            "bvid": episode.get("bvid", ""),
            "ep_id": episode.get("ep_id", 0),
            "season_id": episode.get("season_id", 0),
            "media_id": episode.get("media_id", 0),
            "pubtime": episode.get("pubtime", 0),
            "badge": episode.get("badge", ""),
            "duration": episode.get("duration", 0),
            "cover_url": episode.get("cover_url", ""),
            "link": episode.get("link"),
            "pid": 0,
            "badge": episode.get("badge", ""),
            "section_title": episode.get("section_title", ""),
            "part_title": episode.get("part_title", ""),
            "collection_title": episode.get("collection_title", ""),
            "series_title": episode.get("series_title", ""),
            "interact_title": episode.get("interact_title", ""),
            "parent_title": episode.get("parent_title", ""),
            "area": episode.get("area", ""),
            "zone": episode.get("zone", ""),
            "subzone": episode.get("subzone", ""),
            "up_name": episode.get("up_name", ""),
            "up_mid": episode.get("up_mid", 0),
            "item_type": "item",
            "type": episode.get("type", 0),
            "bangumi_type": episode.get("bangumi_type", ""),
            "template_type": episode.get("template_type", 0)
        }

class Episode:
    class Utils:
        @staticmethod
        def get_first_episode():
            def condition(episode: dict):
                return episode.get("item_type") == "item"
            
            return Filter.travarsal_episode(condition)
        
        @staticmethod
        def search_episode(keywords: str, show_matches_only: bool):
            def condition(episode: dict):
                title = episode.get("title")

                return keywords in title
            
            EpisodeInfo.clear_filter_data()

            if keywords and show_matches_only:
                Filter.travarsal_episode_all(condition)
            else:
                EpisodeInfo.filted_data = EpisodeInfo.data.copy()

class Filter:
    @staticmethod
    def travarsal_episode(condition: Callable):
        def traveral(data: list | dict):
            if isinstance(data, dict):
                if condition(data):
                    return data
                
                if entries := data.get("entries"):
                    if rtn := traveral(entries):
                        return rtn

            elif isinstance(data, list):
                for entry in data:
                    if rtn := traveral(entry):
                        return rtn
        
        return traveral(EpisodeInfo.data.copy())
    
    @staticmethod
    def travarsal_episode_all(condition: Callable):
        def traveral(data: list | dict):
            if isinstance(data, dict):
                if condition(data):
                    EpisodeInfo.add_item(EpisodeInfo.root_pid, data, target_data = EpisodeInfo.filted_data)
                else:
                    if entries := data.get("entries"):
                        traveral(entries)

            elif isinstance(data, list):
                for entry in data:
                    traveral(entry)

        traveral(EpisodeInfo.data.copy())

    @classmethod
    def episode_display_mode(cls, reset: bool = False):
        EpisodeInfo.clear_filter_data()

        if reset:
            Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                episode = cls.travarsal_episode(EpisodeInfo.parser.condition_single)

            case EpisodeDisplayType.In_Section:
                episode = cls.travarsal_episode(EpisodeInfo.parser.condition_in_section)

            case EpisodeDisplayType.All:
                EpisodeInfo.filted_data = EpisodeInfo.data.copy()
                return
        
        EpisodeInfo.add_item(EpisodeInfo.root_pid, episode, target_data = EpisodeInfo.filted_data)