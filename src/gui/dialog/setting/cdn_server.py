from PySide6.QtCore import Qt, QSize

from qfluentwidgets import SubtitleLabel, BodyLabel, CommandBar, Action, FluentIcon

from gui.dialog.setting.edit_host import EditHostDialog
from gui.component.setting import EditActionWidget
from gui.component.widget import DragTreeWidget
from gui.component.dialog import DialogBase

from util.common import Translator, config, ExtendedFluentIcon, DefaultValue

class CDNServerDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.cdn_list = config.get(config.cdn_server_list).copy()

        self.init_cdn_list()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Service Provider CDN"), self)
        tip_lab = BodyLabel(self.tr("Drag items to reorder. Higher items have higher priority."))

        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.command_bar.addAction(self._create_action(FluentIcon.ADD_TO, self.tr("Add"), self.on_add_new_host))
        self.command_bar.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Reset to Default"), self.on_reset_to_default))

        self.cdn_server_list = DragTreeWidget(self)
        self.cdn_server_list.setWidgetColumn(2)
        self.cdn_server_list.itemMoved.connect(self.on_item_moved)
        self.cdn_server_list.header().setStretchLastSection(False)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(tip_lab)
        self.viewLayout.addWidget(self.command_bar)
        self.viewLayout.addWidget(self.cdn_server_list)

        self.adjust_widget_size()

    def init_cdn_list(self):
        self.cdn_server_list.setColumnHeaders(
            [
                self.tr("Node"),
                self.tr("Provider"),
                self.tr("Actions")
            ],
            [
                400,
                100,
                75
            ]
        )

        self.cdn_server_list.clear()
        
        for index, entry in enumerate(self.cdn_list):
            host = entry.get("host", "")
            provider_key = entry.get("provider", "")
            provider = Translator.CDN_SERVER_PROVIDER(provider_key)

            self._add_item([host, provider], provider_key = provider_key, index = index)

        header = self.cdn_server_list.header()

        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)

    def on_add_new_host(self):
        entry = {
            "host": "",
            "provider": "CUSTOM"
        }

        dialog = EditHostDialog("", self)

        if dialog.exec():
            entry["host"] = dialog.cdn_node

            self._add_item(
                [
                    dialog.cdn_node,
                    Translator.CDN_SERVER_PROVIDER("CUSTOM")
                ],
                provider_key = "CUSTOM",
                index = self.cdn_server_list.topLevelItemCount()
            )

            self.cdn_list.append(entry)

            self.cdn_server_list.scrollToBottom()

    def on_reset_to_default(self):
        self.cdn_list = DefaultValue.cdn_server_list.copy()

        self.init_cdn_list()

    def on_edit_host(self, index: int):
        entry = self.cdn_list[index]

        dialog = EditHostDialog(entry.get("host", ""), self)
        
        if dialog.exec() == DialogBase.DialogCode.Accepted:
            entry["host"] = dialog.cdn_node

            item = self.cdn_server_list.topLevelItem(index)
            item.setText(0, dialog.cdn_node)

            self.cdn_list[index] = entry

    def on_remove_host(self, index: int):
        self.cdn_server_list.takeTopLevelItem(index)

        self.cdn_list.pop(index)
        
        # 移除节点后需重新绑定后面节点的索引
        self._rebind_action_widgets()

    def on_item_moved(self, current_row: int, target_row: int):
        # 1. 同步内部数据列表的位置
        item_data = self.cdn_list.pop(current_row)
        self.cdn_list.insert(target_row, item_data)
        
        # 2. 重新绑定所有 Widget（因为拖拽后每个行的固化 index 发生了错位）
        self._rebind_action_widgets()

    def _rebind_action_widgets(self):
        for i in range(self.cdn_server_list.topLevelItemCount()):
            item = self.cdn_server_list.topLevelItem(i)
            widget = self._create_action_widget(i)
            self.cdn_server_list.setItemWidget(item, 2, widget)

    def accept(self):
        config.set(config.cdn_server_list, self.cdn_list.copy())

        return super().accept()
    
    def _add_item(self, args: list, provider_key: str, index: int):
        item = self.cdn_server_list.add_item(args)
        item.setData(1, Qt.ItemDataRole.UserRole, provider_key)

        widget = self._create_action_widget(index)

        self.cdn_server_list.setItemWidget(item, 2, widget)

    def _create_action_widget(self, index: int):
        action_widget = EditActionWidget(self.cdn_server_list)
        action_widget.edit_btn.clicked.connect(lambda: self.on_edit_host(index))
        action_widget.delete_btn.clicked.connect(lambda: self.on_remove_host(index))

        return action_widget
    
    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)

        return action
    
    def adjust_widget_size(self):
        parent_size: QSize = self.parent().size()

        width = parent_size.width() * 0.45
        height = parent_size.height() * 0.6

        self.widget.setMinimumWidth(max(650, width))
        self.widget.setMinimumHeight(max(450, height))