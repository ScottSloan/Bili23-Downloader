from typing import Dict, Union

from utils.config import Config

from utils.common.data_type import CommentData
from utils.common.formatter import FormatUtils

class Danmaku:
    def __init__(self):
        self.width = 1920
        self.height = 1080

        self.font_size = 48

        self.scroll_duration = 10
        self.stay_duration = 5

        self.data: Dict[int, Dict[int, Union[None, CommentData]]] = {
            1: {i + 1: None for i in range(int(self.height / self.font_size))}
        }

    def get_dialogue_list(self, data: list):
        dialogue_list = []

        for entry in data:
            match entry["mode"]:
                case 1 | 2 | 3:
                    # 普通弹幕
                    dialogue = self.process_normal_comment(entry)

                case _:
                    dialogue = None

                # case 4:
                #     # 底部弹幕
                #     left, top = self.calc_pos()

                #     style = f"\\an2\\pos({left}, {top})"

                # case 5:
                #     # 顶部弹幕
                #     left, top = self.calc_pos()

                #     style = f"\\an8\\pos({left}, {top})"

            dialogue_list.append(dialogue)

        dialogue_list = [entry for entry in dialogue_list if entry]

        return dialogue_list

    def process_normal_comment(self, data: dict):
        start_time = data.get("progress") / 1000
        end_time = start_time + self.scroll_duration
        text = data.get("content")

        row = self.check_row(1, self.get_comment_data(start_time, text))

        if row:
            height = self.calc_row(row)

            style = f"\\move({self.width}, {height}, -{len(text) * self.font_size}, {height})"

            return (FormatUtils.format_ass_time(start_time), FormatUtils.format_ass_time(end_time), f"{{{style}}}{text}")

    def calc_pos(self):
        width = Config.Basic.ass_style.get("width")
        height = Config.Basic.ass_style.get("height")

        return width / 2, 0
    
    def calc_row(self, row: int):
        return (row - 1) * self.font_size
    
    def check_row(self, type: int, new_row: CommentData):
        for key, value in self.data.get(type).items():
            if value:
                if new_row.start_time >= value.start_time + value.length / value.speed:
                    self.data.get(type)[key] = new_row
                    return key
            else:
                self.data.get(type)[key] = new_row
                return key

    def get_comment_data(self, start_time: int, text: str):
        data = CommentData()
        data.start_time = start_time
        data.text = text
        data.length = len(text) * self.font_size
        data.speed = (data.length + self.width) / self.scroll_duration

        return data

    def get_dialogue_data(self, from_time: int, to_time: int, text: str):
        return {
            "from": from_time,
            "to": to_time,
            "text": text
        }
    
    def get_style(self):
        return f"Default,微软雅黑,{self.font_size},&H33FFFFFF,&H33FFFFFF,&H33000000,&H33000000,0,0,0,0,100,100,0,0,1,2,0,7,0,0,0,0"
    