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
