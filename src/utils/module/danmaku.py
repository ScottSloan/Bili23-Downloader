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

        rows = {i + 1: None for i in range(int(self.height / self.font_size))}

        self.data: Dict[int, Dict[int, Union[None, CommentData]]] = {i + 1: rows.copy() for i in range(3)}

    def get_dialogue_list(self, data: list):
        dialogue_list = []

        for entry in data:
            match entry["mode"]:
                case 1 | 2 | 3:
                    # 普通弹幕
                    dialogue = self.process_comment(entry, 1, self.scroll_duration)

                case 4:
                    # 底部弹幕
                    dialogue = self.process_comment(entry, 3, self.stay_duration)

                case 5:
                    # 顶部弹幕
                    dialogue = self.process_comment(entry, 2, self.stay_duration)

                case _:
                    dialogue = None

            dialogue_list.append(dialogue)

        dialogue_list = [entry for entry in dialogue_list.copy() if entry]

        return dialogue_list

    def process_comment(self, data: dict, type: int, duration: int):
        start_time = data.get("progress") / 1000
        end_time = start_time + duration
        text = data.get("content")
        color = data.get("color")

        comment_data = self.check_row(type, self.get_comment_data(start_time, end_time, text))

        if comment_data:
            height = self.calc_row(comment_data.row)

            match type:
                case 1:
                    # 普通弹幕
                    style = f"\\move({self.width}, {height}, -{len(text) * self.font_size}, {height})"

                case 2:
                    # 顶部弹幕
                    left, top = self.calc_pos(comment_data.row)

                    style = f"\\an8\\pos({left},{top})"

                case 3:
                    # 底部弹幕
                    left, top = self.calc_pos(comment_data.row)

                    style = f"\\an2\\pos({left},{top})"

            if color and color != 16777215:
                style += f"\\c&H{self.get_color(color)}&"

            return (FormatUtils.format_ass_time(start_time), FormatUtils.format_ass_time(comment_data.end_time), f"{{{style}}}{text}")    

    def calc_pos(self, row: int):
        return int(self.width / 2), self.calc_row(row)
    
    def calc_row(self, row: int):
        return (row - 1) * self.font_size
    
    def check_row(self, type: int, new_row: CommentData):
        def set_row(new_row: CommentData, row: int):
            new_row.row = row

            self.data.get(type)[row] = new_row

        def type_normal():
            for key, value in self.data.get(type).items():
                if value:
                    speed = int((value.width + self.width) / (value.end_time - value.start_time))

                    if new_row.start_time >= value.start_time + value.width / speed:
                        new_row.end_time = new_row.start_time + (new_row.width + self.width) / speed

                        set_row(new_row, key)
                        return new_row
                else:
                    set_row(new_row, key)
                    return new_row
        
        def type_top():
            for key, value in self.data.get(type).items():
                if value:
                    if new_row.start_time >= value.end_time:
                        set_row(new_row, key)
                        return new_row

                else:
                    set_row(new_row, key)
                    return new_row
        
        def type_btm():
            for key, value in reversed(list(self.data.get(type).items())):
                if value:
                    if new_row.start_time >= value.end_time:
                        set_row(new_row, key)
                        return new_row

                else:
                    set_row(new_row, key)
                    return new_row
    
        match type:
            case 1:
                return type_normal()

            case 2:
                return type_top()
            
            case 3:
                return type_btm()
            
            case _:
                return None

    def get_comment_data(self, start_time: int, end_time: int, text: str):
        data = CommentData()
        data.start_time = start_time
        data.end_time = end_time
        data.text = text
        data.width = len(text) * self.font_size

        return data

    def get_dialogue_data(self, from_time: int, to_time: int, text: str):
        return {
            "from": from_time,
            "to": to_time,
            "text": text
        }
    
    def get_style(self):
        return f"Default,微软雅黑,{self.font_size},&H33FFFFFF,&H33FFFFFF,&H33000000,&H33000000,0,0,0,0,100,100,0,0,1,2,0,7,0,0,0,0"
    
    def get_color(self, color: int):
        hex_color = hex(color)[2:]

        return hex_color[4:] + hex_color[2:4] + hex_color[:2]
    