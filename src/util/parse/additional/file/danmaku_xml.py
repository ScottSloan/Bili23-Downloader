from textwrap import indent
from typing import List
import re

xml_base = """<?xml version="1.0" encoding="UTF-8"?>
<i>
    <chatserver>chat.bilibili.com</chatserver>
    <chatid>{cid}</chatid>
    <mission>0</mission>
    <maxlimit>1500</maxlimit>
    <state>0</state>
    <real_name>0</real_name>
    <source>k-v</source>
{comments}
</i>"""

class DanmakuXML:
    def __init__(self, dict_list: List[dict], cid: int):
        self.dict_list = dict_list
        self.cid = cid

    def generate(self):
        return xml_base.format(
            cid = self.cid,
            comments = self._comments()
        )

    def _comments(self):
        comment_elements = []

        for entry in self.dict_list:
            comment_elements.append(
                indent(
                    """<d p="{stime},{mode},{size},{color},{date},0,{uhash},{dmid}">{text}</d>""".format(
                        stime = self._ms_to_s(entry.get("stime", 0)),
                        mode = entry.get("mode", 1),
                        size = entry.get("size", 25),
                        color = entry.get("color", 16777215),
                        date = entry.get("date", 0),
                        uhash = entry.get("uhash", 0),
                        dmid = entry.get("dmid", 0),
                        weight = entry.get("weight", 1),
                        text = self._filter_invalid_characters(entry.get("text", ""))
                    ),
                    "    "
                )
            )

        return "\n".join(comment_elements)
    
    def _filter_invalid_characters(self, text: str) -> str:
        # 过滤非法XML字符并转义特殊字符
        # 这里简单地移除控制字符，并转义 &, <, >, ", '

        text = re.sub(r'[\x00-\x1F\x7F]', '', text)  # 移除控制字符
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')

        return text

    def _ms_to_s(self, ms: int) -> str:
        return f"{ms / 1000:.5f}"
    