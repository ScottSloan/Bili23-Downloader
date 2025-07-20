from typing import List

from utils.common.formatter import FormatUtils

class XML:
    @classmethod
    def make(cls, data: List[dict], cid: int):
        contents = ""

        contents += cls.get_header()
        contents += cls.get_comments(data, cid)

        return contents

    @staticmethod
    def get_header():
        return '<?xml version="1.0" encoding="UTF-8"?>'
    
    @staticmethod
    def get_i_attr(cid: int):
        attr = {
            "chatserver": "chat.bilibili.com",
            "chatid": cid,
            "mission": 0,
            "maxlimit": 100000,
            "state": 0,
            "real_name": 0,
            "source": "k-v"
        }

        return "".join([f"<{key}>{value}</{key}>" for key, value in attr.items()])
    
    @classmethod
    def get_comments(cls, data: List[dict], cid: int):
        comments = ""

        for index, entry in enumerate(data):
            attr = ",".join([FormatUtils.format_xml_timestamp(entry.get("progress") / 1000), str(entry.get("mode")), str(entry.get("fontsize")), str(entry.get("color")), str(entry.get("ctime")), "0", entry.get("midHash"), str(entry.get("id")), str(index + 1)])

            comments += f'<d p="{attr}">{entry.get("content")}</d>'

        return f"<i>{cls.get_i_attr(cid)}{comments}</i>"

