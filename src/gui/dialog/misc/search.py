from PySide6.QtWidgets import QVBoxLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, LineEdit, RadioButton

from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory

class SearchDialog(DialogBase):
    def __init__(self, server_search_available: bool = False, current_keyword: str = "", paginated: bool = False, parent = None):
        super().__init__(parent = parent)

        # 当前解析结果是否来自支持服务端搜索的接口（个人空间、收藏夹、历史记录、稍后再看）
        self.server_search_available = server_search_available
        # 当前链接中已生效的搜索关键词，用于回显
        self.current_keyword = current_keyword
        # 当前解析结果是否存在分页，决定本地筛选是否覆盖得到全部内容
        self.paginated = paginated

        self.server_search = False

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Search"))

        self.keywords_box = LineEdit(self)
        self.keywords_box.setPlaceholderText(self.tr("Enter keywords to search"))
        self.keywords_box.setClearButtonEnabled(True)
        self.keywords_box.setText(self.current_keyword)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.keywords_box)

        if self.server_search_available:
            self.viewLayout.addSpacing(10)
            self.viewLayout.addLayout(self.get_scope_layout())

        elif self.paginated:
            # 接口不支持搜索的分页内容（如合集），本地筛选只能覆盖当前页
            self.tip_lab = BodyLabel(self.tr("Only the current page can be filtered. To search the full list, parse all pages first."), self)
            self.tip_lab.setWordWrap(True)

            self.viewLayout.addSpacing(10)
            self.viewLayout.addWidget(self.tip_lab)

        self.widget.setMinimumWidth(450)

    def get_scope_layout(self):
        # 此类内容存在分页，本地筛选只能覆盖当前页，因此额外提供交由服务端搜索全部内容的方式
        scope_lab = BodyLabel(self.tr("Search scope"), self)

        self.filter_page_radio = RadioButton(self.tr("Filter the current page only"), self)
        self.search_all_radio = RadioButton(self.tr("Search all pages, results are provided by Bilibili"), self)

        # 已经处于搜索状态时，默认继续使用服务端搜索，便于直接修改关键词
        if self.current_keyword:
            self.search_all_radio.setChecked(True)
        else:
            self.filter_page_radio.setChecked(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scope_lab)
        layout.addWidget(self.filter_page_radio)
        layout.addWidget(self.search_all_radio)

        return layout

    def use_server_search(self):
        return self.server_search_available and self.search_all_radio.isChecked()

    def validate(self):
        # 服务端搜索允许留空，表示清除关键词，重新解析出完整内容
        if self.use_server_search():
            return True

        if self.keywords_box.text().strip() == "":
            self.keywords_box.setFocus()
            self.keywords_box.setError(True)

            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", self.tr("Please enter search keywords"))

            return False

        return True

    def accept(self):
        self.keywords = self.keywords_box.text().strip()
        self.server_search = self.use_server_search()

        return super().accept()
