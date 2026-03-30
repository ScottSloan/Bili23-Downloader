from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtCore import Qt

from qfluentwidgets import BodyLabel, CheckBox, ComboBox, ColorPickerButton

from gui.component.widget import SpinBox, DoubleSpinBox

from util.common.data import subtitles_alignment_map
from util.common import Translator, Color

class FontGroup(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        font_name_lab = BodyLabel(self.tr("Font Family"), self)
        self.font_name_choice = ComboBox(self)
        self.font_name_choice.addItems(QFontDatabase.families())
        self.font_name_choice.setFixedWidth(150)
        font_size_lab = BodyLabel(self.tr("Font Size"), self)
        self.font_size_spin = SpinBox(ignore_wheel = True, parent = self)
        self.font_size_spin.setRange(1, 1000)
        self.font_size_spin.setFixedWidth(150)

        self.font_bold_chk = CheckBox(self.tr("Bold"), self)
        self.font_italic_chk = CheckBox(self.tr("Italic"), self)
        self.font_underline_chk = CheckBox(self.tr("Underline"), self)
        self.font_strike_chk = CheckBox(self.tr("Strikeout"), self)

        font_type_layout = QGridLayout()
        font_type_layout.addWidget(font_name_lab, 0, 0)
        font_type_layout.addWidget(font_size_lab, 0, 1)
        font_type_layout.addWidget(self.font_name_choice, 1, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        font_type_layout.addWidget(self.font_size_spin, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft)

        font_style_layout = QHBoxLayout()
        font_style_layout.setContentsMargins(0, 5, 0, 0)
        font_style_layout.setSpacing(25)
        font_style_layout.addWidget(self.font_bold_chk)
        font_style_layout.addWidget(self.font_italic_chk)
        font_style_layout.addWidget(self.font_underline_chk)
        font_style_layout.addWidget(self.font_strike_chk)
        font_style_layout.addStretch()

        group_layout = QVBoxLayout(self)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addLayout(font_type_layout)
        group_layout.addLayout(font_style_layout)

    def init_data(self, data: dict):
        self.font_name_choice.setCurrentText(data.get("name"))
        self.font_size_spin.setValue(data.get("size"))

        self.font_bold_chk.setChecked(data.get("bold"))
        self.font_italic_chk.setChecked(data.get("italic"))
        self.font_underline_chk.setChecked(data.get("underline"))
        self.font_strike_chk.setChecked(data.get("strike"))

    def get_data(self):
        return {
            "name": self.font_name_choice.currentText(),
            "size": self.font_size_spin.value(),
            "bold": self.font_bold_chk.isChecked(),
            "italic": self.font_italic_chk.isChecked(),
            "underline": self.font_underline_chk.isChecked(),
            "strike": self.font_strike_chk.isChecked()
        }

class BorderGroup(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        border_lab = BodyLabel(self.tr("Outline (px)"), self)
        self.border_spin = DoubleSpinBox(ignore_wheel = True, parent = self)
        self.border_spin.setDecimals(1)
        self.border_spin.setValue(1.0)
        
        shadow_lab = BodyLabel(self.tr("Shadow (px)"), self)
        self.shadow_spin = DoubleSpinBox(ignore_wheel = True, parent = self)
        self.shadow_spin.setDecimals(1)
        self.shadow_spin.setValue(0.0)

        border_layout = QGridLayout(self)
        border_layout.setContentsMargins(0, 0, 0, 5)
        border_layout.addWidget(border_lab, 0, 0)
        border_layout.addWidget(shadow_lab, 0, 1)
        border_layout.addWidget(self.border_spin, 1, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        border_layout.addWidget(self.shadow_spin, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft)

        border_layout.setColumnMinimumWidth(0, 150)
        border_layout.setColumnMinimumWidth(1, 150)
    
    def init_data(self, data: dict):
        self.border_spin.setValue(data.get("border"))
        self.shadow_spin.setValue(data.get("shadow"))

    def get_data(self):
        return {
            "border": self.border_spin.value(),
            "shadow": self.shadow_spin.value()
        }
    
class ColorGroup(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        primary_color_lab = BodyLabel(self.tr("Primary Color"), self)
        self.primary_color_btn = ColorPickerButton(QColor("#ffffff"), self.tr("Primary Color"), self, True)
        secondary_color_lab = BodyLabel(self.tr("Secondary Color"), self)
        self.secondary_color_btn = ColorPickerButton(QColor("#ffffff"), self.tr("Secondary Color"), self, True)

        border_color_lab = BodyLabel(self.tr("Outline Color"), self)
        self.border_color_btn = ColorPickerButton(QColor("#ffffff"), self.tr("Outline Color"), self, True)
        shadow_color_lab = BodyLabel(self.tr("Shadow Color"), self)
        self.shadow_color_btn = ColorPickerButton(QColor("#ffffff"), self.tr("Shadow Color"), self, True)

        color_layout = QGridLayout(self)
        color_layout.setContentsMargins(0, 0, 0, 5)
        color_layout.addWidget(primary_color_lab, 0, 0)
        color_layout.addWidget(secondary_color_lab, 0, 1)
        color_layout.addWidget(self.primary_color_btn, 1, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        color_layout.addWidget(self.secondary_color_btn, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft)
        color_layout.addWidget(border_color_lab, 2, 0)
        color_layout.addWidget(shadow_color_lab, 2, 1)
        color_layout.addWidget(self.border_color_btn, 3, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        color_layout.addWidget(self.shadow_color_btn, 3, 1, alignment = Qt.AlignmentFlag.AlignLeft)
    
    def init_data(self, data: dict):
        self.primary_color_btn.setColor(Color.ass_alpha_to_qcolor(data.get("primary")))
        self.secondary_color_btn.setColor(Color.ass_alpha_to_qcolor(data.get("secondary")))
        self.border_color_btn.setColor(Color.ass_alpha_to_qcolor(data.get("border")))
        self.shadow_color_btn.setColor(Color.ass_alpha_to_qcolor(data.get("shadow")))

    def get_data(self):
        return {
            "primary": Color.qcolor_to_ass_alpha(self.primary_color_btn.color),
            "secondary": Color.qcolor_to_ass_alpha(self.secondary_color_btn.color),
            "border": Color.qcolor_to_ass_alpha(self.border_color_btn.color),
            "shadow": Color.qcolor_to_ass_alpha(self.shadow_color_btn.color),
        }
    
class MarginGroup(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        margin_left_lab = BodyLabel(self.tr("Left Margin (px)"), self)
        self.margin_left_spin = SpinBox(ignore_wheel = True, parent = self)
        self.margin_left_spin.setRange(-1000, 1000)
        self.margin_left_spin.setValue(10)
        self.margin_left_spin.setFixedWidth(150)
        margin_right_lab = BodyLabel(self.tr("Right Margin (px)"), self)
        self.margin_right_spin = SpinBox(ignore_wheel = True, parent = self)
        self.margin_right_spin.setRange(-1000, 1000)
        self.margin_right_spin.setValue(10)
        self.margin_right_spin.setFixedWidth(150)
        margin_vert_lab = BodyLabel(self.tr("Vertical Margin (px)"), self)
        self.margin_vert_spin = SpinBox(ignore_wheel = True, parent = self)
        self.margin_vert_spin.setRange(-1000, 1000)
        self.margin_vert_spin.setValue(20)
        self.margin_vert_spin.setFixedWidth(150)

        margin_layout = QGridLayout(self)
        margin_layout.setContentsMargins(0, 0, 0, 0)
        margin_layout.addWidget(margin_left_lab, 0, 0)
        margin_layout.addWidget(margin_right_lab, 0, 1)
        margin_layout.addWidget(self.margin_left_spin, 1, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        margin_layout.addWidget(self.margin_right_spin, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft)
        margin_layout.addWidget(margin_vert_lab, 2, 0)
        margin_layout.addWidget(self.margin_vert_spin, 3, 0, alignment = Qt.AlignmentFlag.AlignLeft)

    def init_data(self, data: dict):
        self.margin_left_spin.setValue(data.get("left"))
        self.margin_right_spin.setValue(data.get("right"))
        self.margin_vert_spin.setValue(data.get("vertical"))

    def get_data(self):
        return {
            "left": self.margin_left_spin.value(),
            "right": self.margin_right_spin.value(),
            "vertical": self.margin_vert_spin.value()
        }
    
class AlignmentGroup(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        alignment_lab = BodyLabel(self.tr("Alignment"), self)
        self.alignment_choice = ComboBox(self)
        self.alignment_choice.setFixedWidth(200)

        group_layout = QVBoxLayout(self)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(alignment_lab)
        group_layout.addWidget(self.alignment_choice)

    def init_data(self, data: int):
        for key, value in subtitles_alignment_map.items():
            text = "{description} ({alignment})".format(
                description = Translator.SUBTITLES_ALIGNMENT(key), 
                alignment = value
            )

            self.alignment_choice.addItem(text, userData = value)

            if value == data:
                self.alignment_choice.setCurrentText(text)

    def get_data(self):
        return self.alignment_choice.currentData()

class AdvancedGroup(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        display_area_lab = BodyLabel(self.tr("Display Area (%)"), parent = self)
        self.display_area_spin = SpinBox(self)
        self.display_area_spin.setFixedWidth(150)
        self.display_area_spin.setRange(10, 100)

        opacity_lab = BodyLabel(self.tr("Opacity (%)"), parent = self)
        self.opacity_spin = SpinBox(self)
        self.opacity_spin.setFixedWidth(150)
        self.opacity_spin.setRange(10, 100)

        scroll_duration_lab = BodyLabel(self.tr("Scroll Duration (s)"), parent = self)
        self.scroll_duration_spin = SpinBox(self)
        self.scroll_duration_spin.setFixedWidth(150)
        self.scroll_duration_spin.setRange(3, 15)

        static_duration_lab = BodyLabel(self.tr("Static Duration (s)"), parent = self)
        self.static_duration_spin = SpinBox(self)
        self.static_duration_spin.setFixedWidth(150)
        self.static_duration_spin.setRange(3, 15)

        minimum_spacing_lab = BodyLabel(self.tr("Minimum Horizontal Spacing (px)"), parent = self)
        self.minimum_horizontal_spacing_spin = SpinBox(self)
        self.minimum_horizontal_spacing_spin.setFixedWidth(150)
        self.minimum_horizontal_spacing_spin.setRange(0, 300)

        group_layout = QGridLayout(self)
        group_layout.setContentsMargins(0, 0, 0, 5)
        group_layout.addWidget(display_area_lab, 0, 0)
        group_layout.addWidget(opacity_lab, 0, 1)
        group_layout.addWidget(self.display_area_spin, 1, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        group_layout.addWidget(self.opacity_spin, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft)
        group_layout.addWidget(scroll_duration_lab, 2, 0)
        group_layout.addWidget(static_duration_lab, 2, 1)
        group_layout.addWidget(self.scroll_duration_spin, 3, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        group_layout.addWidget(self.static_duration_spin, 3, 1, alignment = Qt.AlignmentFlag.AlignLeft)
        group_layout.addWidget(minimum_spacing_lab, 4, 0)
        group_layout.addWidget(self.minimum_horizontal_spacing_spin, 5, 0, alignment = Qt.AlignmentFlag.AlignLeft)

    def init_data(self, data: dict):
        self.display_area_spin.setValue(data.get("display_area"))
        self.opacity_spin.setValue(data.get("opacity"))

        self.scroll_duration_spin.setValue(data.get("scroll_duration"))
        self.static_duration_spin.setValue(data.get("static_duration"))
        self.minimum_horizontal_spacing_spin.setValue(data.get("minimum_gap"))

    def get_data(self):
        return {
            "display_area": self.display_area_spin.value(),
            "opacity": self.opacity_spin.value(),
            "scroll_duration": self.scroll_duration_spin.value(),
            "static_duration": self.static_duration_spin.value(),
            "minimum_gap": self.minimum_horizontal_spacing_spin.value()
        }

class ResolutionGroup(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        screen_width_lab = BodyLabel(self.tr("Screen Width (px)"), self)

        self.screen_width_box = SpinBox(ignore_wheel = True, parent = self)
        self.screen_width_box.setRange(1, 10000)
        self.screen_width_box.setValue(1280)
        self.screen_width_box.setFixedWidth(150)

        screen_height_lab = BodyLabel(self.tr("Screen Height (px)"), self)

        self.screen_height_box = SpinBox(ignore_wheel = True, parent = self)
        self.screen_height_box.setRange(1, 10000)
        self.screen_height_box.setValue(720)
        self.screen_height_box.setFixedWidth(150)

        group_layout = QGridLayout(self)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(screen_width_lab, 0, 0)
        group_layout.addWidget(screen_height_lab, 0, 1)
        group_layout.addWidget(self.screen_width_box, 1, 0, alignment = Qt.AlignmentFlag.AlignLeft)
        group_layout.addWidget(self.screen_height_box, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft)

    def init_data(self, data: dict):
        self.screen_width_box.setValue(data.get("width"))
        self.screen_height_box.setValue(data.get("height"))

    def get_data(self):
        return {
            "width": self.screen_width_box.value(),
            "height": self.screen_height_box.value()
        }