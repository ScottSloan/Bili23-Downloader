from typing import List, Dict, Union

from utils.config import Config

from utils.common.model.data_type import CommentData
from utils.common.style.color import Color
from utils.common.formatter.formatter import FormatUtils

class Json2ASS:
    def __init__(self, video_width: int, video_height: int):
        self.video_width = video_width
        self.video_height = video_height

        danmaku_style = Config.Basic.ass_style.get("danmaku")

        self.font_size = danmaku_style.get("font_size")

        self.scroll_duration = danmaku_style.get("scroll_duration")
        self.stay_duration = danmaku_style.get("stay_duration")

        rows = {i + 1: None for i in range(int(self.video_height / self.font_size))}

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
                    style = f"\\move({self.video_width}, {height}, -{len(text) * self.font_size}, {height})"

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
        return int(self.video_width / 2), self.calc_row(row)
    
    def calc_row(self, row: int):
        return (row - 1) * self.font_size
    
    def check_row(self, type: int, new_row: CommentData):
        def set_row(new_row: CommentData, row: int):
            new_row.row = row

            self.data.get(type)[row] = new_row

        def type_normal():
            for key, value in self.data.get(type).items():
                if value:
                    speed = int((value.width + self.video_width) / (value.end_time - value.start_time))

                    if new_row.start_time >= value.start_time + value.width / speed:
                        new_row.end_time = new_row.start_time + (new_row.width + self.video_width) / speed

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
    
class DanmakuASSFile:
    def __init__(self, json_data: List[dict], resolution: dict):
        self.json_data = json_data
        self.video_width = resolution.get("width")
        self.video_height = resolution.get("height")

    def get_contents(self):
        sections = (self.get_script_info_section(), self.get_styles_section(), self.get_events_section())

        return "\n\n".join(sections)

    def get_script_info_section(self):
        data = [
            (";", "Script generated by Bili23 Downloader"),
            (";", "https://bili23.scott-sloan.cn"),
            ("ScriptType", "v4.00+"),
            ("PlayResX", self.video_width),
            ("PlayResY", self.video_height),
            ("Aspect Ratio", f"{self.video_width}:{self.video_height}"),
            ("Collisions", "Normal"),
            ("WrapStyle", "2"),
            ("ScaledBorderAndShadow", "yes"),
        ]

        return self.format_section("Script Info", data)
    
    def get_styles_section(self):
        data = [
            ("Format", "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"),
            ("Style", self.get_danmaku_style())
        ]

        return self.format_section("V4+ Styles", data)
    
    def get_events_section(self):
        data = [
            ("Format", "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"),
        ]
        
        converter = Json2ASS(self.video_width, self.video_height)

        dialogues = [
            ("Dialogue", f"2,{start_time},{end_time},Default,,0,0,0,,{content}")
            for (start_time, end_time, content) in converter.get_dialogue_list(self.json_data)
        ]

        data.extend(dialogues)

        return self.format_section("Events", data)

    def get_danmaku_style(self):
        danmaku_style = Config.Basic.ass_style.get("danmaku")

        style_data = {
            "Name": "Default",
            "Fontname": danmaku_style.get("font_name"),
            "Fontsize": danmaku_style.get("font_size"),
            "PrimaryColour": "&H00FFFFFF",
            "SecondaryColour": "&H00FFFFFF",
            "OutlineColour": "&H00000000",
            "BackColour": "&H00000000",
            "Bold": danmaku_style.get("bold"),
            "Italic": danmaku_style.get("italic"),
            "Underline": danmaku_style.get("underline"),
            "StrikeOut": danmaku_style.get("strikeout"),
            "ScaleX": 100,
            "ScaleY": 100,
            "Spacing": 0,
            "Angle": 0,
            "BorderStyle": 1,
            "Outline": danmaku_style.get("border"),
            "Shadow": danmaku_style.get("shadow"),
            "Alignment": 7,
            "MarginL": 0,
            "MarginR": 0,
            "MarginV": 0,
            "Encoding": 1
        }

        return ",".join([str(value) for value in style_data.values()])
    
    def format_section(self, title: str, data: list):
        return f"[{title}]\n" + "\n".join([f"{key}: {value}" if key != ";" else f"; {value}" for (key, value) in data])