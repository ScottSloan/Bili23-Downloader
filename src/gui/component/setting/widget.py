from PySide6.QtWidgets import QWidget, QHBoxLayout

from qfluentwidgets import SwitchButton, QConfig, OptionsConfigItem, ComboBox, FluentIcon, IndicatorPosition, qconfig

from gui.component.widget import TransparentToolButton

class SettingSwitchButton(SwitchButton):
    def __init__(self, config_item: QConfig, parent = None):
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

