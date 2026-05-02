from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from qfluentwidgets import (
    SwitchButton, OptionsConfigItem, ComboBox, FluentIcon, IndicatorPosition, Slider, qconfig,
    RangeConfigItem, isDarkTheme, ConfigItem
)

from gui.component.widget import TransparentToolButton

from util.common import config

class SettingSwitchButton(SwitchButton):
    def __init__(self, config_item: ConfigItem, parent = None):
        super().__init__(parent = parent, indicatorPos = IndicatorPosition.RIGHT)

        self.config_item = config_item

        self.setChecked(qconfig.get(config_item))
        self.checkedChanged.connect(self.on_check_changed)

    def on_check_changed(self, isChecked: bool):
        qconfig.set(self.config_item, isChecked)

class SettingComboBox(ComboBox):
    def __init__(self, config_item: OptionsConfigItem, texts: list, save = True, parent = None):
        super().__init__(parent)

        self.config_item = config_item

        self.optionToText = {o: t for o, t in zip(config_item.options, texts)}

        for text, option in zip(texts, config_item.options):
            self.addItem(text, userData = option)

        self.setCurrentText(self.optionToText[qconfig.get(config_item)])

        if save:
            self.currentIndexChanged.connect(self.on_current_index_changed)

    def on_current_index_changed(self, index: int):
        qconfig.set(self.config_item, self.itemData(index))

class SettingSlider(QWidget):
    def __init__(self, config_item: RangeConfigItem, parent = None):
        super().__init__(parent)

        self.configItem = config_item

        self.setContentsMargins(0, 0, 0, 0)

        self.slider = Slider(Qt.Orientation.Horizontal, self)
        self.slider.setMinimumWidth(230)
        self.slider.setRange(*config_item.range)
        self.slider.setValue(config_item.value)

        self.value_label = QLabel(self)
        self.value_label.setNum(config_item.value)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.value_label)
        layout.addWidget(self.slider)

        self.slider.valueChanged.connect(self.__onValueChanged)

        config.themeChanged.connect(self.__setQSS)

        self.__setQSS()

    def __onValueChanged(self, value: int):
        """ slider value changed slot """
        self.setValue(value)

    def setValue(self, value: int):
        qconfig.set(self.configItem, value)
        self.value_label.setNum(value)
        self.value_label.adjustSize()
        self.slider.setValue(value)

    def __setQSS(self):
        if isDarkTheme():
            self.value_label.setStyleSheet("color: rgb(159, 159, 159);")
        else:
            self.value_label.setStyleSheet("color: rgb(96, 96, 96);")

class EditActionWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.edit_btn = TransparentToolButton(FluentIcon.EDIT, self)
        self.edit_btn.setToolTip(self.tr("Edit"))

        self.delete_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self.delete_btn.setToolTip(self.tr("Delete"))

        action_layout = QHBoxLayout(self)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addWidget(self.edit_btn)
        action_layout.addWidget(self.delete_btn)

class ParseActionWidget(EditActionWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.edit_btn.setIcon(FluentIcon.SEARCH)
        self.edit_btn.setToolTip(self.tr("Parse"))

class InsertActionWidget(EditActionWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.edit_btn.setIcon(FluentIcon.ADD_TO)
        self.edit_btn.setToolTip(self.tr("Insert"))

        self.delete_btn.hide()

