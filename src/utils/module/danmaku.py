from utils.config import Config

class Danmaku:
    @classmethod
    def convert_protobuf_to_ass(cls, data: list):
        for entry in data:
            match entry["mode"]:
                case 1 | 2 | 3:
                    pass

                case 4:
                    # 底部弹幕
                    left, top = cls.calc_pos()

                    style = f"\\an2\\pos({left}, {top})"

                case 5:
                    # 顶部弹幕
                    left, top = cls.calc_pos()

                    style = f"\\an8\\pos({left}, {top})"

    @staticmethod
    def calc_pos():
        width = Config.Basic.ass_style.get("width")
        height = Config.Basic.ass_style.get("height")

        return width / 2, 0