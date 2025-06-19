import json
import time
from typing import List, Callable

from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.common.request import RequestUtils

from utils.parse.parser import Parser

class Node:
    def __init__(self, cid: int, title: str):
        self.cid: int = cid
        self.title: str = title
        self.options: List[Option] = []

    def to_dict(self):
        return {
            "cid": self.cid,
            "title": self.title,
            "options": [option.to_dict() for option in self.options]
        }
    
class Option:
    def __init__(self, edge_id: int, name: str):
        self.edge_id: int = edge_id
        self.name: str = name
        self.target_node_cid: int = None
        self.show: bool = True
        self.accessed: bool = False

    def to_dict(self):
        return {
            "edge_id": self.edge_id,
            "name": self.name,
            "accessed": self.accessed,
            "target_node_cid": self.target_node_cid
        }

class InteractVideoInfo:
    aid: int = 0
    cid: int = 0
    bvid: str = ""
    url: str = ""
    title: str = ""
    graph_version: int = 0

    node_list: List[Node] = []

    @classmethod
    def add_to_node_list(cls, cid: int, title: str, options: dict):
        node = Node(cid, title)

        if "questions" in options:
            question = options["questions"][0]

            for entry in question["choices"]:
                option = Option(entry["id"], entry["option"])
                option.target_node_cid = entry["cid"]
                option.show = question["pause_video"]

                node.options.append(option)

        cls.node_list.append(node)
    
    @classmethod
    def check_node_exists(cls, cid: int):
        for node in cls.node_list:
            if node.cid == cid:
                return True
            
        return False

    @classmethod
    def get_option(cls):
        for node in cls.node_list:
            for option in node.options:
                if not option.accessed:
                    option.accessed = True

                    if not cls.check_node_exists(option.target_node_cid):
                        return option
                
    @classmethod
    def nodes_to_dict(cls):
        nodes_dict = {
            "nodes": [node.to_dict() for node in cls.node_list],
        }
    
        return json.dumps(nodes_dict, ensure_ascii = False, indent = 2)

    @classmethod
    def clear_video_info(cls):
        cls.aid = 0
        cls.cid = 0
        cls.bvid = ""
        cls.url = ""
        cls.title = ""
        cls.graph_version = 0

        cls.node_list.clear()

class InteractVideoParser(Parser):
    def __init__(self, callback: Callable):
        super().__init__()

        self.callback = callback

    def get_video_interactive_graph_version(self):
        # 获取互动视频 graph_version
        params = {
            "aid": InteractVideoInfo.aid,
            "cid": InteractVideoInfo.cid
        }

        url = f"https://api.bilibili.com/x/player/wbi/v2?aid={InteractVideoInfo.aid}&cid={InteractVideoInfo.cid}&{WbiUtils.encWbi(params)}"

        req = RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = InteractVideoInfo.url, sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        if "interaction" in info:
            InteractVideoInfo.graph_version = info["interaction"]["graph_version"]

    def get_video_interactive_edge_info(self, cid: int, edge_id: int = 0):
        # 获取互动视频模块信息
        url = f"https://api.bilibili.com/x/stein/edgeinfo_v2?bvid={InteractVideoInfo.bvid}&graph_version={InteractVideoInfo.graph_version}&edge_id={edge_id}"

        req = RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = InteractVideoInfo.url, sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        InteractVideoInfo.add_to_node_list(cid, info["title"], info["edges"])

        self.callback(info["title"])

        return InteractVideoInfo.get_option()
    
    def parse_interactive_video_episodes(self):
        option = self.get_video_interactive_edge_info(cid = InteractVideoInfo.cid)
        
        while option:
            option = self.get_video_interactive_edge_info(option.target_node_cid, option.edge_id)
            
            time.sleep(0.1)