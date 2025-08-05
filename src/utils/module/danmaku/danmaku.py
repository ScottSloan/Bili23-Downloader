from typing import Dict, Union

from utils.config import Config

from utils.common.model.data_type import CommentData, ASSStyle
from utils.common.formatter.formatter import FormatUtils
from utils.common.style.color import Color

class Danmaku:
    def __init__(self, resolution: dict):
        self.width = resolution.get("width")
        self.height = resolution.get("height")

        danmaku = Config.Basic.ass_style.get("danmaku")

        self.font_size = danmaku.get("font_size")

        self.scroll_duration = danmaku.get("scroll_duration")
        self.stay_duration = danmaku.get("stay_duration")

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

                    style = f"\\an8\\pos({left}, {top})"

                case 3:
                    # 底部弹幕
                    left, top = self.calc_pos(comment_data.row)

                    style = f"\\an2\\pos({left}, {top})"

            if color and color != 16777215:
                style += f"\\c{Color.convert_to_ass_color(hex(color)[2:])}"

            return (FormatUtils.format_ass_timestamp(start_time), FormatUtils.format_ass_timestamp(comment_data.end_time), f"{{{style}}}{text}")    

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
            for key, value in reversed(list(self.data.get(2).items())):
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
    
    def get_ass_style(self):
        danmaku = Config.Basic.ass_style.get("danmaku")

        ASSStyle.Name = "Default"
        ASSStyle.Fontname = danmaku.get("font_name")
        ASSStyle.Fontsize = danmaku.get("font_size")
        ASSStyle.PrimaryColour = "&H00FFFFFF"
        ASSStyle.SecondaryColour = "&H00FFFFFF"
        ASSStyle.OutlineColour = "&H00000000"
        ASSStyle.BackColour = "&H00000000"
        ASSStyle.Bold = danmaku.get("bold")
        ASSStyle.Italic = danmaku.get("italic")
        ASSStyle.Underline = danmaku.get("underline")
        ASSStyle.StrikeOut = danmaku.get("strikeout")
        ASSStyle.ScaleX = 100
        ASSStyle.ScaleY = 100
        ASSStyle.Spacing = 0
        ASSStyle.Angle = 0
        ASSStyle.BorderStyle = 1
        ASSStyle.Outline = danmaku.get("border")
        ASSStyle.Shadow = danmaku.get("shadow")
        ASSStyle.Alignment = 7
        ASSStyle.MarginL = 0
        ASSStyle.MarginR = 0
        ASSStyle.MarginV = 0
        ASSStyle.Encoding = 1

        return ASSStyle.to_string()