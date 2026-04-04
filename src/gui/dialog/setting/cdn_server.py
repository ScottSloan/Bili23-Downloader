from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt

from qfluentwidgets import SubtitleLabel, BodyLabel, CommandBar, Action, FluentIcon

from gui.component.setting.widget import ActionWidget
from gui.component.widget import EditDragTreeWidget
from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory
from util.common import Translator, config

class CDNServerDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.cdn_list = config.get(config.cdn_server_list).copy()

        self.init_cdn_list()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Service Provider CDN"), self)
        tip_lab = BodyLabel(self.tr("Drag to reorder, double-click to edit. Higher items have higher priority."))

        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        add_action = Action(FluentIcon.ADD_TO, self.tr("Add"), self)
        add_action.triggered.connect(self.on_add_new_host)
        delete_action = Action(FluentIcon.REMOVE_FROM, self.tr("Delete"), self)
        delete_action.triggered.connect(self.on_remove_host)

        self.command_bar.addAction(add_action)
        self.command_bar.addAction(delete_action)

        self.cdn_server_list = EditDragTreeWidget(self)
        self.cdn_server_list.setColumnEditable(1, True)
        self.cdn_server_list.setReorderEnabled(True)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(tip_lab)
        self.viewLayout.addWidget(self.command_bar)
        self.viewLayout.addWidget(self.cdn_server_list)

        self.widget.setMinimumWidth(650)

    def init_cdn_list(self):
        self.cdn_server_list.setColumnHeaders(
            [
                self.tr("No."),
                self.tr("Node"),
                self.tr("Provider"),
                self.tr("Actions")
            ],
            [
                60,
                350,
                100,
                75
            ]
        )
        
        for index, entry in enumerate(self.cdn_list):
            host = entry.get("host", "")
            provider_key = entry.get("provider", "")
            provider = Translator.CDN_SERVER_PROVIDER(provider_key)

            self._add_item([str(index + 1), host, provider], provider_key = provider_key, edit_column = 1, index = index)

    def on_add_new_host(self):
        self._add_item(
            [
                str(self.cdn_server_list.topLevelItemCount() + 1),
                "",
                Translator.CDN_SERVER_PROVIDER("CUSTOM")
            ],
            provider_key = "CUSTOM",
            edit_column = 1,
            index = self.cdn_server_list.topLevelItemCount()
        )

    def on_remove_host(self):
        item = self.cdn_server_list.selectedItems()

        if not item:
            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", self.tr("Please select an item to delete"))
            return

        self.cdn_server_list.remove_item(item[0])

    def validate(self):
        self.cdn_list.clear()

        for index in range(self.cdn_server_list.topLevelItemCount()):
            item = self.cdn_server_list.topLevelItem(index)

            if item.text(1) == "":
                self.show_top_toast_message(ToastNotificationCategory.ERROR, "", self.tr("Node address cannot be empty"))

                self.cdn_server_list.scrollToItem(item)
                return False

            entry = {
                "host": item.text(1),
                "provider": item.data(2, Qt.ItemDataRole.UserRole)
            }

            self.cdn_list.append(entry)

        return True
    
    def accept(self):
        config.set(config.cdn_server_list, self.cdn_list.copy())

        return super().accept()
    
    def _add_item(self, args: list, provider_key: str, edit_column: int, index: int):
        item = self.cdn_server_list.add_item(args, edit_column = edit_column)
        item.setData(2, Qt.ItemDataRole.UserRole, provider_key)

        widget = self.create_action_widget(index)

        self.cdn_server_list.setItemWidget(item, 3, widget)

    def create_action_widget(self, index: int):
        action_widget = ActionWidget(self.cdn_server_list)
        #action_widget.delete_btn.clicked.connect(lambda: self.on_remove_host())

        return action_widget