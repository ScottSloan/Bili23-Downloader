import textwrap
from typing import List

from utils.common.formatter.formatter import FormatUtils

class DanmakuXMLFile:
    def __init__(self, json_data: List[dict], cid: int):
        self.json_data = json_data
        self.cid = cid

    def get_contents(self):
        contents = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <i>
                <chatserver>chat.bilibili.com</chatserver>
                <chatid>{cid}</chatid>
                <mission>0</mission>
                <maxlimit>100000</maxlimit>
                <state>0</state>
                <real_name>0</real_name>
                <source>k-v</source>
                {d_elements}
            </i>
            """.format(cid = self.cid, d_elements = self.get_d_elements()))

        return contents
    
    def get_d_elements(self):
        p_elements = [f"""<d p="{self.get_p_attr(entry)}">{entry.get("content")}</d>""" for entry in self.json_data]

        return "\n                ".join(p_elements)
    
    def get_p_attr(self, entry: dict):
        return ",".join([
            FormatUtils.format_xml_timestamp(entry.get("progress") / 1000),
            str(entry.get("mode")),
            str(entry.get("fontsize")),
            str(entry.get("color")),
            str(entry.get("ctime")),
            "0",
            str(entry.get("midHash")),
            str(entry.get("id")),
            str(entry.get("weight"))
        ])
