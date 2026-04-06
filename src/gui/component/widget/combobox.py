from PySide6.QtCore import Signal

from qfluentwidgets import ComboBox

from util.common.data import cid_list

class CidComboBox(ComboBox):
    """
    CidComboBox 用于选择国家/地区代码。
    """

    def __init__(self, parent = None):
        super().__init__(parent)

        for entry in cid_list:
            self.addItem(f"+{entry['code']}", userData = entry['code'])

class DictComboBox(ComboBox):
    def __init__(self, parent = None):
        super().__init__(parent)

    def init_dict_data(self, data_map: dict, translation_map: dict, current_data = None):
        # 加载字典数据，并根据 translation_map 进行翻译显示
        for key, value in data_map.items():
            text = translation_map.get(key)

            self.addItem(text, userData = value)

            if value == current_data:
                self.setCurrentText(text)

    def set_current_data(self, data):
        index = self.findData(data)

        if index != -1:
            self.setCurrentIndex(index)

class SeasonComboBox(ComboBox):
    changeSeason = Signal(str)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.series_title = ""
        self.currentIndexChanged.connect(self.on_season_changed)

    def update_data(self, season_data: dict):
        season_list = season_data.get("season_list", [])
        series_title = season_data.get("series_title", "")
        season_id = season_data.get("season_id", "")

        if series_title == self.series_title:
            # 在同一系列中切换季，不需要更新数据，避免切换季时重置为第一项
            return

        self.blockSignals(True)
        self.clear()

        for entry in season_list:
            self.addItem(entry["title"], userData = entry["url"])

            if entry["season_id"] == season_id:
                self.setCurrentText(entry["title"])
            
        self.show()
        self.blockSignals(False)

        self.series_title = series_title

    def on_season_changed(self, index: int):
        url = self.itemData(index)

        if url:
            self.changeSeason.emit(url)
