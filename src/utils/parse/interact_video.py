import json
import time
from typing import List, Callable

from utils.config import Config
from utils.tool_v2 import RequestTool
from utils.auth.wbi import WbiUtils

from utils.common.enums import StatusCode
from utils.common.exception import GlobalException

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
    graph_version: int = 0

    node_list: List[Node] = []

    @staticmethod
    def add_to_node_list(cid: int, title: str, options: dict):
        if not InteractVideoInfo.check_node_exists(cid):
            node = Node(cid, title)

            for entry in options:
                option = Option(entry["id"], entry["option"])
                option.target_node_cid = entry["cid"]

                node.options.append(option)

            InteractVideoInfo.node_list.append(node)
    
    @staticmethod
    def check_node_exists(cid: int):
        for node in InteractVideoInfo.node_list:
            if node.cid == cid:
                return True
            
        return False

    @staticmethod
    def get_option():
        for node in InteractVideoInfo.node_list:
            for option in node.options:
                if not option.accessed:
                    option.accessed = True
                    return option
                
    @staticmethod
    def nodes_to_dict():
        nodes_dict = {
            "nodes": [node.to_dict() for node in InteractVideoInfo.node_list],
        }
    
        return json.dumps(nodes_dict, ensure_ascii = False, indent = 2)

class InteractVideoParser:
    def __init__(self, callback: Callable):
        self.callback = callback

    def get_video_interactive_graph_version(self):
        # 获取互动视频 graph_version
        params = {
            "aid": InteractVideoInfo.aid,
            "cid": InteractVideoInfo.cid
        }

        url = f"https://api.bilibili.com/x/player/wbi/v2?aid={InteractVideoInfo.aid}&cid={InteractVideoInfo.cid}&{WbiUtils.encWbi(params)}"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = InteractVideoInfo.url, sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        if "interaction" in info:
            InteractVideoInfo.graph_version = info["interaction"]["graph_version"]

    def get_video_interactive_edge_info(self, cid: int, edge_id: int = 0):
        # 获取互动视频模块信息
        url = f"https://api.bilibili.com/x/stein/edgeinfo_v2?bvid={InteractVideoInfo.bvid}&graph_version={InteractVideoInfo.graph_version}&edge_id={edge_id}"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = InteractVideoInfo.url, sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        InteractVideoInfo.add_to_node_list(cid, info["title"], info["edges"]["questions"][0]["choices"])

        self.callback(info["title"])

        return InteractVideoInfo.get_option()
    
    def parse_interactive_video_episodes(self):
        option = self.get_video_interactive_edge_info(cid = InteractVideoInfo.cid)
        
        while option:
            option = self.get_video_interactive_edge_info(option.target_node_cid, option.edge_id)
            
            time.sleep(0.1)

        InteractVideoInfo.graph_data = json.dumps(InteractVideoInfo.nodes_to_dict(), ensure_ascii = False, indent = 2)

    def check_json(self, data: dict):
        # 检查接口返回状态码
        status_code = data["code"]

        if status_code != StatusCode.Success.value:
            raise GlobalException(message = data["message"], code = status_code)