from qfluentwidgets import FluentIconBase, Theme, qconfig

from enum import Enum

class ExtendedFluentIcon(FluentIconBase, Enum):
    # 在原有 FluentIcon 的基础上添加新的图标
    PIN = "pin"
    EXIT = "exit"
    TODO = "todo"
    LIST = "list"
    SORT = "sort"
    CLOCK = "clock"
    ALBUM = "album"
    CLEAR = "clear"
    RETRY = "retry"
    SELECT = "select"
    RENAME = "rename"
    SERVER = "server"
    COMMENT = "comment"
    OPTIONS = "options"
    NUMBERS = "numbers"
    DOCUMENT = "document"
    FAVORITE = "favorite"
    SUBTITLES = "subtitles"
    TEST_CUBE = "test_cube"
    CLIPBOARD = "clipboard"
    SELECT_ALL = "select_all"
    CHOOSE_PAGE = "choose_page"
    SORT_REVERSE = "sort_reverse"
    FILE_SETTINGS = "file_settings"
    FAST_DOWNLOAD = "fast_download"
    SINGLE_CHOICE = "single_choice"
    APPLICATION_WINDOW = "application_window"
    DOUBLE_RIGHT_ARROWS = "double_right_arrows"

    def path(self, theme = Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme

        return f':/bili23/icon/{theme.value.lower()}/{self.value}.svg'

