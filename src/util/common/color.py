from PySide6.QtGui import QColor

class Color:
    @staticmethod
    def qcolor_to_hex(color: QColor) -> str:
        return color.name(QColor.NameFormat.HexRgb).upper()
    
    @staticmethod
    def hex_to_qcolor(hex_str: str) -> QColor:
        return QColor(hex_str)
    
    @staticmethod
    def qcolor_to_ass_alpha(color: QColor) -> str:
        return f"&H{(255 - color.alpha()):02X}{color.blue():02X}{color.green():02X}{color.red():02X}"
    
    @staticmethod
    def qcolor_to_ass(color: QColor) -> str:
        return f"&H{color.blue():02X}{color.green():02X}{color.red():02X}&"
    
    @staticmethod
    def ass_alpha_to_qcolor(ass_str: str) -> QColor:
        ass_str = ass_str.lstrip("&H")

        r = ass_str[6:8]
        g = ass_str[4:6]
        b = ass_str[2:4]
        a = ass_str[0:2]

        return QColor(int(r, 16), int(g, 16), int(b, 16), 255 - int(a, 16))
    
    @staticmethod
    def ass_to_qcolor(ass_str: str) -> QColor:
        ass_str = ass_str.lstrip("&H").rstrip("&")

        r = ass_str[4:6]
        g = ass_str[2:4]
        b = ass_str[0:2]

        return QColor(int(r, 16), int(g, 16), int(b, 16), 0)