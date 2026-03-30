from enum import Enum

from qfluentwidgets import StyleSheetBase, Theme, qconfig

class StyleSheet(StyleSheetBase, Enum):
    BUTTON = "button"
    FLUENT_DIALOG = "fluent_dialog"
    SETTING_INTERFACE = "setting_interface"
    SCROLLABLE_DIALOG = "scrollable_dialog"

    def path(self, theme = Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme

        return f":/bili23/qss/{theme.value.lower()}/{self.value}.qss"