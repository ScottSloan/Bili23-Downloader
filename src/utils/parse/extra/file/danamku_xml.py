from typing import List

from utils.common.formatter.formatter import FormatUtils

class DanmakuXMLFile:
    def __init__(self, json_data: List[dict], cid: int):
        self.json_data = json_data
        self.cid = cid

    def get_contents(self):
        contents = ""

        contents += """<?xml version="1.0" encoding="UTF-8"?>\n"""
        contents += f"<i>\n    {self.get_i_element()}\n{self.get_d_elements()}</i>"

        return contents

    def get_i_element(self):
        attr = {
            "chatserver": "chat.bilibili.com",
            "chatid": self.cid,
            "mission": 0,
            "maxlimit": 100000,
            "state": 0,
            "real_name": 0,
            "source": "k-v"
        }

        return "\n    ".join([f'<{k}>{v}</{k}>' for k, v in attr.items()])
    
    def get_d_elements(self):
        comments = ""

        for entry in self.json_data:
            p_attr = [
                FormatUtils.format_xml_timestamp(entry.get("progress") / 1000),
                str(entry.get("mode")),
                str(entry.get("fontsize")),
                str(entry.get("color")),
                str(entry.get("ctime")),
                "0",
                str(entry.get("midHash")),
                str(entry.get("id")),
                str(entry.get("weight"))
            ]

            comments += f'    <d p="{",".join(p_attr)}">{entry.get("content")}</d>\n'

        return comments
