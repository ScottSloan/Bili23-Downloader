from qfluentwidgets import FluentIconBase, Theme, qconfig

from enum import Enum

class ExtendedFluentIcon(FluentIconBase, Enum):
    # 在原有 FluentIcon 的基础上添加新的图标
    PIN = "pin"
    EXIT = "exit"
    CLEAR = "clear"
    RETRY = "retry"
    SERVER = "server"
    COMMENT = "comment"
    OPTIONS = "options"
    NUMBERS = "numbers"
    DOCUMENT = "document"
    SUBTITLES = "subtitles"
    CLIPBOARD = "clipboard"
    FAST_DOWNLOAD = "fast_download"

    def path(self, theme = Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme

        return f':/bili23/icon/{theme.value.lower()}/{self.value}.svg'

