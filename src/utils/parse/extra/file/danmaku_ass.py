import math

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

        self.subtitle_obstruct = danmaku_style.get("subtitle_obstruct")
        self.area = (danmaku_style.get("area", 5) * 20) / 100
        self.alpha = math.ceil(255 - 2.55 * danmaku_style.get("alpha", 80)) # alpha = 255 - 2.55 * percent

        self.scroll_duration = 17 - 2 * danmaku_style.get("speed", 3) # value = 17 - 2 * speed
        self.stay_duration = 8 - danmaku_style.get("speed", 3) # value = 8 - speed
        self.density = 2 - danmaku_style.get("density", 1) # value = 2 - density

        self.init_data_table()

    def init_data_table(self):
        ratio = 1.0

        if self.subtitle_obstruct:
            ratio = 0.85

        ratio = min(ratio, self.area)

        row_count = math.floor(ratio * (self.video_height / self.font_size))

        rows = {i + 1: None for i in range(row_count)}

        self.data: Dict[int, Dict[int, Union[None, CommentData]]] = {i + 1: rows.copy() for i in range(3)}

    def get_dialogue_list(self, data: list):
        dialogue_list = []

        for entry in data:
            match entry["mode"]:
                case 1 | 2 | 3:
                    # 普通弹幕
                    comment = self.process_comment(entry, 1, self.scroll_duration)

                case 4:
                    # 底部弹幕
                    comment = self.process_comment(entry, 3, self.stay_duration)

                case 5:
                    # 顶部弹幕
                    comment = self.process_comment(entry, 2, self.stay_duration)

                case _:
                    comment = None

            dialogue_list.append(comment)

        dialogue_list = [entry for entry in dialogue_list.copy() if entry]

        return dialogue_list

    def process_comment(self, data: dict, type: int, duration: int):
        start_time = data.get("progress") / 1000
        end_time = start_time + duration
        content = data.get("content")
        color = data.get("color")

        comment_data = self.check_row(type, self.get_comment_data(start_time, end_time, content))

        if comment_data:
            height = self.calc_row_height(comment_data.row)

            match type:
                case 1:
                    # 普通弹幕
                    style = f"\\move({self.video_width}, {height}, -{len(content) * self.font_size}, {height})"

                case 2:
                    # 顶部弹幕
                    left, top = self.calc_pos(comment_data.row)

                    style = f"\\an8\\pos({left}, {top})"

                case 3:
                    # 底部弹幕
                    left, top = self.calc_pos(comment_data.row)

                    style = f"\\an2\\pos({left}, {top})"

            if color:
                style += f"\\c{Color.convert_to_ass_bgr_color(Color.dec_to_hex(color))}"
                style += f"\\alpha{Color.convert_to_ass_a_color(self.alpha)}"

            return (
                FormatUtils.format_ass_timestamp(start_time),
                FormatUtils.format_ass_timestamp(comment_data.end_time),
                f"{{{style}}}{content}"
            )

    def calc_pos(self, row: int):
        return int(self.video_width / 2), self.calc_row_height(row)
    
    def calc_row_height(self, row: int):
        return (row - 1) * self.font_size
    
    def check_row(self, type: int, new_comment: CommentData):
        def set_row(new_row: CommentData, row: int):
            new_row.row = row

            self.data.get(type)[row] = new_row

            return new_row

        def check_normal_comment():
            for row, previous_comment in self.data.get(type).items():
                if previous_comment:
                    previous_speed = math.ceil((previous_comment.width + self.video_width) / (previous_comment.end_time - previous_comment.start_time))

                    if self.density == 3:
                        previous_shown_time = new_comment.start_time
                    else:
                        previous_shown_time = (previous_comment.start_time + previous_comment.width / previous_speed) + self.density

                    if new_comment.start_time >= previous_shown_time:
                        duration = max((new_comment.width + self.video_width) / previous_speed, self.scroll_duration)
                        distance = math.ceil((new_comment.start_time - previous_comment.start_time) * previous_speed)
                        
                        # 速度补偿
                        ratio = distance / self.video_width
                        offset = 0.3 - 0.2 * math.exp(-2.77 * ratio)

                        duration -= offset

                        new_comment.end_time = new_comment.start_time + duration

                        return set_row(new_comment, row)
                else:
                    return set_row(new_comment, row)
        
        def check_top_comment():
            for row, previous_comment in self.data.get(type).items():
                if previous_comment:
                    if new_comment.start_time >= previous_comment.end_time:
                        return set_row(new_comment, row)
                else:
                    return set_row(new_comment, row)
        
        def check_bottom_comment():
            for row, previous_comment in reversed(list(self.data.get(2).items())):
                if previous_comment:
                    if new_comment.start_time >= previous_comment.end_time:
                        return set_row(new_comment, row)
                else:
                    return set_row(new_comment, row)
    
        match type:
            case 1:
                return check_normal_comment()

            case 2:
                return check_top_comment()
            
            case 3:
                return check_bottom_comment()
            
            case _:
                return None

    def get_comment_data(self, start_time: int, end_time: int, text: str):
        data = CommentData()
        data.start_time = start_time
        data.end_time = end_time
        data.text = text
        data.width = len(text) * self.font_size

        return data
    
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
            "ScaleX": danmaku_style.get("scale_x"),
            "ScaleY": danmaku_style.get("scale_y"),
            "Spacing": danmaku_style.get("spacing"),
            "Angle": danmaku_style.get("angle"),
            "BorderStyle": 3 if danmaku_style.get("non_alpha") else 1,
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