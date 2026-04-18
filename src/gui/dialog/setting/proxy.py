from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QGridLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, LineEdit, PushButton, MessageBox

from gui.component.setting import SettingComboBox
from gui.component.dialog import DialogBase

from util.network import NetworkRequestWorker, Proxy
from util.thread import AsyncTask
from util.common import config

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ProxyDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Configure Proxy Server"), self)

        proxy_type_lab = BodyLabel(self.tr("Proxy Type"))
        self.proxy_type_choice = SettingComboBox(config.proxy_type, ["HTTP"], save = False, parent = self)
        self.proxy_type_choice.setFixedWidth(120)

        server_lab = BodyLabel(self.tr("Address"), self)
        self.server_box = LineEdit(self)
        self.server_box.setPlaceholderText(self.tr("Proxy server address"))
        self.server_box.setText(config.get(config.proxy_server))

        port_validator = QRegularExpressionValidator(r"^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$")

        port_lab = BodyLabel(self.tr("Port"), self)
        self.port_box = LineEdit(self)
        self.port_box.setPlaceholderText(self.tr("Proxy server port"))
        self.port_box.setValidator(port_validator)
        self.port_box.setText(str(config.get(config.proxy_port)))

        uname_lab = BodyLabel(self.tr("Username"), self)
        self.uname_box = LineEdit(self)
        self.uname_box.setPlaceholderText(self.tr("Optional"))
        self.uname_box.setText(config.get(config.proxy_uname))

        password_lab = BodyLabel(self.tr("Password"), self)
        self.password_box = LineEdit(self)
        self.password_box.setPlaceholderText(self.tr("Optional"))
        self.password_box.setText(config.get(config.proxy_password))

        self.test_btn = PushButton(self.tr("Test"), self)
        self.test_btn.setMaximumWidth(100)

        grid_layout = QGridLayout()
        grid_layout.addWidget(server_lab, 0, 0)
        grid_layout.addWidget(port_lab, 0, 1)
        grid_layout.addWidget(self.server_box, 1, 0)
        grid_layout.addWidget(self.port_box, 1, 1)
        grid_layout.addWidget(uname_lab, 2, 0)
        grid_layout.addWidget(password_lab, 2, 1)
        grid_layout.addWidget(self.uname_box, 3, 0)
        grid_layout.addWidget(self.password_box, 3, 1)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(proxy_type_lab)
        self.viewLayout.addWidget(self.proxy_type_choice)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(grid_layout)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.test_btn)

        self.widget.setMinimumWidth(500)

        self.test_btn.clicked.connect(self.on_test)

    def on_test(self):
        url = "https://api.bilibili.com/x/web-interface/zone"

        worker = NetworkRequestWorker(url)
        worker.success.connect(self.on_test_success)
        worker.error.connect(self.on_test_error)

        proxy = Proxy()
        proxy.set_data(self.get_data())

        worker.set_proxies(proxy.get_proxies())

        AsyncTask.run(worker)

    def on_test_success(self, response: Dict[str, Any]):
        data = response.get("data", {})

        ip = data.get("addr", "")
        country = data.get("country", "")
        province = data.get("province", "")
        city = data.get("city", "")
        isp = data.get("isp", "")

        location_parts = [part for part in [country, province, city] if part]
        location = " ".join(location_parts) if location_parts else self.tr("Unknown")

        dialog = MessageBox(
            self.tr("Network Test Result"),
            self.tr("IP: {ip}\nLocation: {location}\nISP: {isp}").format(
                ip = ip if ip else self.tr("Unknown"),
                location = location,
                isp = isp if isp else self.tr("Unknown")
            ),
            self
        )
        dialog.hideCancelButton()

        dialog.exec()

    def on_test_error(self, error: str):
        logger.exception("代理测试失败: %s", error)

        dialog = MessageBox(self.tr("Network Test Failed"), error, self)
        dialog.hideCancelButton()

        dialog.exec()

    def get_data(self):
        return {
            "type": self.proxy_type_choice.currentData(),
            "server": self.server_box.text(),
            "port": int(self.port_box.text()),
            "uname": self.uname_box.text(),
            "password": self.password_box.text()
        }

    def accept(self):
        config.set(config.proxy_type, self.proxy_type_choice.currentData())

        config.set(config.proxy_server, self.server_box.text())
        config.set(config.proxy_port, int(self.port_box.text()))
        config.set(config.proxy_uname, self.uname_box.text())
        config.set(config.proxy_password, self.password_box.text())

        return super().accept()
    