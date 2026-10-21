from PySide6.QtCore import Qt

from qfluentwidgets import SubtitleLabel, BodyLabel, CaptionLabel

from gui.component.dialog import DialogBase

from util.network.error import NetworkErrorInfo, NetworkErrorKind
from util.common.enum import ProxyMode

class NetworkErrorDialog(DialogBase):
    """
    解析因网络问题失败时，代替「解析失败」通知弹出，告诉用户问题出在哪、该怎么做。

    原先的通知只会原样贴出底层报错，例如「由于目标计算机积极拒绝，无法连接」——
    用户看不出这与代理有关，更不知道去哪里改。点「打开代理设置」时对话框以 accept 结束，
    跳转由调用方负责
    """
    def __init__(self, info: NetworkErrorInfo, error_message: str, parent = None):
        super().__init__(parent)

        self.info = info
        self.error_message = error_message

        self.init_UI()

    def init_UI(self):
        title, lines = self.get_content()

        caption_lab = SubtitleLabel(title, self)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(5)

        for line in lines:
            lab = BodyLabel(line, self)
            lab.setWordWrap(True)

            self.viewLayout.addWidget(lab)

        if self.error_message:
            # 原始报错留着给用户反馈问题时复制
            detail_lab = CaptionLabel(self.tr("Error details: {message}").format(message = self.error_message), self)
            detail_lab.setWordWrap(True)
            detail_lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            self.viewLayout.addSpacing(5)
            self.viewLayout.addWidget(detail_lab)

        self.yesButton.setText(self.tr("Open Proxy Settings"))
        self.cancelButton.setText(self.tr("Close"))

        # 直连时被风控，代理设置里没有可改的，留着这个按钮只会把用户引到无关的地方
        if self.info.kind == NetworkErrorKind.RISK_CONTROL and not self.info.proxy_mode:
            self.yesButton.hide()

        self.widget.setFixedWidth(480)

    def get_content(self):
        if self.info.kind == NetworkErrorKind.PROXY:
            return self.tr("Unable to connect through the proxy"), self.get_proxy_lines()

        if self.info.kind == NetworkErrorKind.RISK_CONTROL:
            return self.tr("Request blocked by Bilibili's risk control"), self.get_risk_control_lines()

        return self.tr("Network connection failed"), [
            self.tr("Unable to connect to the Bilibili server."),
            self.tr("What you can do:"),
            self.tr("1. Check that your network connection is working"),
            self.tr("2. Check whether a firewall or security software is blocking this program"),
            self.tr("3. If your network can only access the Internet through a proxy, configure it in Settings → Advanced → Proxy Mode")
        ]

    def get_proxy_lines(self):
        if self.info.proxy_mode == ProxyMode.MANUAL:
            lines = [
                self.tr("The program is connecting through the manually configured proxy, but the connection failed. The proxy server may be offline, or its address or port may be incorrect.")
            ]

            steps = [
                self.tr("1. Make sure the proxy server is running, then parse again"),
                self.tr("2. Check the proxy server address and port in Settings → Advanced → Proxy Mode, or choose \"Do not use proxy\" there. The change takes effect after restarting the program")
            ]

        else:
            # 默认就是跟随系统代理，用户多半不知道程序在走代理，这一点要先讲清楚
            lines = [
                self.tr("By default the program follows the system proxy, but the connection through it failed. This usually means the proxy software has been closed or its port has changed, while the system proxy setting is still in effect.")
            ]

            steps = [
                self.tr("1. Start the proxy software, then parse again"),
                self.tr("2. If you don't need a proxy, go to Settings → Advanced → Proxy Mode and choose \"Do not use proxy\". The change takes effect after restarting the program")
            ]

        if self.info.proxy_address:
            lines.append(self.tr("Proxy server: {address}").format(address = self.info.proxy_address))

        return lines + [self.tr("What you can do:")] + steps

    def get_risk_control_lines(self):
        lines = [
            self.tr("Bilibili has flagged requests from your current network environment and temporarily blocked access. This usually happens when too many requests are sent in a short time, or when your IP address has been flagged.")
        ]

        if self.info.proxy_address:
            lines.append(self.tr("Proxy server: {address}").format(address = self.info.proxy_address))

        lines += [
            self.tr("What you can do:"),
            self.tr("1. Switch to a different network environment, such as a mobile hotspot, or restart your router to get a new IP address"),
            self.tr("2. Wait a while before parsing again, and avoid parsing too frequently")
        ]

        if self.info.proxy_mode:
            # 风控按出口 IP 判定，走代理时被标记的往往是代理节点，而不是用户自己的网络
            lines.append(self.tr("3. Requests are currently sent through a proxy, whose IP address may have been flagged. Switch to another proxy node, or choose \"Do not use proxy\" in Settings → Advanced → Proxy Mode. The change takes effect after restarting the program"))

        return lines
