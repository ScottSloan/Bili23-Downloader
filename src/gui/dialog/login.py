from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from qfluentwidgets import (
    BodyLabel, ImageLabel, LineEdit, HyperlinkButton
)

from gui.component.widget import IndeterminateProgressPushButton, CidComboBox, SectionLabel
from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory, QRCodeScanStatus
from util.auth import SMS, Captcha, SMSInfo, QRCode
from util.common import signal_bus

class LoginDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._closing = False
        self._resources_cleaned = False

        self.init_utils()

        self.init_UI()

    def init_UI(self):
        # 左侧为二维码登录区域
        scan_lab = SectionLabel(self.tr("Scan QR Code to Log In"))

        self.qrcode_img = ImageLabel(self)
        self.qrcode_img.setFixedSize(160, 160)
        
        self.scan_status_lab = BodyLabel(self.tr("Scan with the Bilibili app to log in"))
        self.scan_status_lab.setMinimumWidth(200)
        self.scan_status_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qrcode_layout = QVBoxLayout()
        qrcode_layout.setSpacing(15)
        qrcode_layout.addWidget(scan_lab, alignment = Qt.AlignmentFlag.AlignHCenter)
        qrcode_layout.addWidget(self.qrcode_img, alignment = Qt.AlignmentFlag.AlignHCenter)
        qrcode_layout.addWidget(self.scan_status_lab, alignment = Qt.AlignmentFlag.AlignHCenter)

        # 右侧为短信登录区域
        sms_login_lab = SectionLabel(self.tr("SMS Login"))

        self.cid_choice = CidComboBox(self)

        self.tel_box = LineEdit(self)
        self.tel_box.setPlaceholderText(self.tr("Enter phone number"))
        self.tel_box.setClearButtonEnabled(True)

        self.verification_box = LineEdit(self)
        self.verification_box.setPlaceholderText(self.tr("Enter verification code"))
        self.verification_box.setClearButtonEnabled(True)

        self.sms_login_btn = IndeterminateProgressPushButton(self.tr("Log In"), self)
        self.sms_login_btn.setFixedWidth(175)

        self.send_verification_btn = HyperlinkButton(self)
        self.send_verification_btn.setText(self.tr("Get Code"))
        self.send_verification_btn.setMinimumWidth(100)

        sms_top_layout = QHBoxLayout()
        sms_top_layout.addWidget(self.cid_choice)
        sms_top_layout.addWidget(self.tel_box)

        sms_bottom_layout = QHBoxLayout()
        sms_bottom_layout.addWidget(self.verification_box)
        sms_bottom_layout.addWidget(self.send_verification_btn)

        sms_layout = QVBoxLayout()
        sms_layout.addStretch()
        sms_layout.addWidget(sms_login_lab, alignment = Qt.AlignmentFlag.AlignHCenter)
        sms_layout.addSpacing(10)
        sms_layout.addLayout(sms_top_layout)
        sms_layout.addLayout(sms_bottom_layout)
        sms_layout.addSpacing(15)
        sms_layout.addWidget(self.sms_login_btn, alignment = Qt.AlignmentFlag.AlignHCenter)
        sms_layout.addStretch()

        login_layout = QHBoxLayout()
        login_layout.addSpacing(40)
        login_layout.addLayout(qrcode_layout)
        login_layout.addSpacing(40)
        login_layout.addLayout(sms_layout)
        login_layout.addSpacing(40)

        self.viewLayout.addSpacing(40)
        self.viewLayout.addLayout(login_layout)
        self.viewLayout.addSpacing(40)

        self.widget.setMinimumWidth(700)

        # 隐藏底部的按钮组，允许通过点击遮罩区域来关闭对话框
        self.buttonGroup.hide()
        self.setClosableOnMaskClicked(True)

        self.sms_countdown_timer = QTimer(self)
        self.sms_countdown_timer.setInterval(1000)

        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.accept)

        self.connect_signals()

    def connect_signals(self):
        self.send_verification_btn.clicked.connect(self.on_send_verification)
        self.sms_login_btn.clicked.connect(self.on_sms_login)

        self.sms_countdown_timer.timeout.connect(self.on_update_sms_countdown)

    def init_utils(self):
        self.sms = SMS(self)
        self.sms.sms_sent.connect(self.on_verfication_sent)
        self.sms.sms_login_success.connect(self.on_sms_login_success)
        self.sms.error.connect(self.show_error_toast_message)

        self.qrcode = QRCode(self)
        self.qrcode.qrcode_generated.connect(self.on_qrcode_update)
        self.qrcode.update_scan_status.connect(self.on_update_scan_status)

        self.captcha = Captcha()

        # 生成二维码，并开始轮询扫码状态
        self.qrcode.generate()
        self.qrcode.start_polling()

    def on_dialog_close(self):
        self._closing = True

        self.cleanup_login_resources()

        signal_bus.login.stop_server.emit()

        self.close_timer.stop()

    def cleanup_login_resources(self):
        if self._resources_cleaned:
            return

        self._resources_cleaned = True

        self.sms_countdown_timer.stop()

        try:
            self.sms.sms_sent.disconnect(self.on_verfication_sent)
        except Exception:
            pass

        try:
            self.sms.sms_login_success.disconnect(self.on_sms_login_success)
        except Exception:
            pass

        try:
            self.sms.error.disconnect(self.show_error_toast_message)
        except Exception:
            pass

        try:
            self.qrcode.qrcode_generated.disconnect(self.on_qrcode_update)
        except Exception:
            pass

        try:
            self.qrcode.update_scan_status.disconnect(self.on_update_scan_status)
        except Exception:
            pass

        self.captcha.cleanup()
        self.sms.cleanup()
        self.qrcode.cleanup()

    def on_send_verification(self):
        # 用户请求发送验证码
        if not self.validate_input(self.tel_box, self.tr("Phone number cannot be empty")):
            return
        
        self.sms.update_cid_tel(
            cid = self.cid_choice.currentData(),
            tel = self.tel_box.text().strip()
        )

        # 进行 Cptcha 验证，成功后发送验证码
        self.captcha.init_geetest()
        
    def on_verfication_sent(self):
        if self._closing:
            return

        # 验证码发送成功
        self.send_verification_btn.setEnabled(False)

        self.sms_countdown_timer.start()

    def on_sms_login(self):
        if not self.validate_input(self.tel_box, self.tr("Phone number cannot be empty")) or not self.validate_input(self.verification_box, self.tr("Verification code cannot be empty")):
            return
        
        self.sms.update_verification_code(self.verification_box.text().strip())

        self.sms.login()

        self.sms_login_btn.setIndeterminateState(True)

    def on_sms_login_success(self):
        if self._closing:
            return

        self.login_success(self.tr("Successfully logged in via SMS"))

        self.sms_login_btn.setIndeterminateState(False)

    def on_qrcode_update(self, pixmap: QPixmap):
        if self._closing:
            return

        # 更新二维码图片
        self.qrcode_img.setPixmap(pixmap)

    def on_update_scan_status(self, status: int):
        if self._closing:
            return

        match status:
            case QRCodeScanStatus.WAITING_FOR_SCAN:
                status_text = self.tr("Scan with the Bilibili app to log in")
            
            case QRCodeScanStatus.WAITING_FOR_CONFIRMATION:
                status_text = self.tr("Confirm login on your device")

            case QRCodeScanStatus.SUCCESS:
                status_text = self.tr("Successfully logged in via QR code")

                self.login_success(status_text)

            case QRCodeScanStatus.EXPIRED:
                status_text = self.tr("QR code has expired")

        self.scan_status_lab.setText(status_text)

    def on_update_sms_countdown(self):
        if self._closing:
            return

        if SMSInfo.countdown == 1:
            self.sms_countdown_timer.stop()

            self.send_verification_btn.setEnabled(True)
            self.send_verification_btn.setText(self.tr("Get Code"))
            return

        SMSInfo.countdown -= 1

        self.send_verification_btn.setText(self.tr("Resend({countdown})").format(countdown = SMSInfo.countdown))
        self.send_verification_btn.setEnabled(False)

    def validate_input(self, target: LineEdit, message: str):
        # 对传入的 widget 进行验证
        if target.text().strip() == "":
            self.show_error_toast_message(message)

            target.setError(True)
            target.setFocus()

            return False
        
        return True
    
    def show_error_toast_message(self, message: str):        
        if self._closing:
            return

        self.show_top_toast_message(ToastNotificationCategory.ERROR, "", message)

        self.sms_login_btn.setIndeterminateState(False)

    def login_success(self, message: str):
        if self._closing:
            return

        self._closing = True

        self.cleanup_login_resources()

        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", message)

        # 延迟关闭对话框，确保用户能看到登录成功的提示
        self.close_timer.start(300)
