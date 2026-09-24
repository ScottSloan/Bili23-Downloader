from PySide6.QtCore import QObject, QTimer, Slot

from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..common.config import config
from ..common.runtime import runtime

from ..network.request import NetworkRequestWorker, RequestType, ResponseType
from ..thread.async_ import AsyncTask
from .base import AuthBase, store_wbi_keys

import logging

logger = logging.getLogger(__name__)

class UserManager(AuthBase, QObject):
    # 弱网下 nav 请求超时是常态，而它一旦定局，这场会话里所有带 wbi 签名的接口
    # 都会跟着失败（详见 util/parse/parser/base.py 里的说明），所以值得多试几次。
    # 间隔逐次拉长而不是定频：这个接口有限流，短时间连续打反而容易被判成风控
    RETRY_DELAYS_MS = (5_000, 15_000, 45_000)

    def __init__(self):
        AuthBase.__init__(self)
        QObject.__init__(self)

        # 单次触发：每次失败单独排下一次，成功或外部触发时作废
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._request_user_info)

        self._retry_index = 0

    def init_user_info(self):
        self.get_user_info()

    def get_user_info(self):
        # 外部触发统一走这里（启动、登录成功、手动刷新）：额度从头算，
        # 并作废排队中的重试 —— 不作废的话这次请求会和那次重试叠成两个
        self._cancel_retry()

        self._request_user_info()

    def _request_user_info(self):
        # 真正发请求的地方。定时重试直接连到这里而不经过 get_user_info，
        # 否则每次重试都会把额度重置回起点，退避就永远不会结束
        url = "https://api.bilibili.com/x/web-interface/nav"

        worker = NetworkRequestWorker(url)
        # 连到本对象的方法而非闭包，Qt 会把回调排队回 GUI 线程；
        # 闭包没有可识别的接收者线程，连接会退化成直连，就地跑在网络请求的子线程里
        worker.success.connect(self.on_get_user_info_success)
        worker.error.connect(self.on_get_user_info_error)

        AsyncTask.run(worker)

    def _cancel_retry(self):
        self._retry_timer.stop()

        self._retry_index = 0

    def _schedule_retry(self) -> bool:
        if self._retry_index >= len(self.RETRY_DELAYS_MS):
            return False

        delay = self.RETRY_DELAYS_MS[self._retry_index]
        self._retry_index += 1

        logger.info("获取用户信息失败，%s 毫秒后重试（第 %s 次）", delay, self._retry_index)

        self._retry_timer.start(delay)

        return True

    def shutdown(self):
        # 退出流程调用。定时器若在此时触发，会在关停过程中拉起新的请求线程，
        # 并把结果投递给已经开始析构的主窗口
        self._retry_timer.stop()

    @Slot(object)
    def on_get_user_info_success(self, response: dict):
        data: dict = response.get("data") or {}

        # 风控（-412）、参数错误等异常响应不带 data.wbi_img，未登录时也有接口不返回。
        # 原先这里直接下标取值，抛出的 KeyError 落在 Qt 槽里会被绑定层吞掉：界面上一声不响，
        # 而签名密钥停在空串，之后每一个带 wbi 签名的请求都会以越界错误失败
        if not store_wbi_keys(data):
            # 服务端已经给出了明确答复，重试大概率还是同样的结果，
            # 所以不走下面的退避重试，直接提示
            self.show_toast_error(
                Translator.ERROR_MESSAGES("USER_INFO_FAILED"),
                response.get("message") or Translator.ERROR_MESSAGES("UNKNOWN_ERROR")
            )

            return

        # 拿到密钥才算这次请求真正成功。这里要连排队中的重试一起作废：
        # 同时有两个请求在飞时（用户在启动请求还没回来时手动登录），
        # 先到的失败可能刚排好一次重试，而它现在已经是多余的了
        self._cancel_retry()

        if data.get("isLogin"):
            runtime.auth.uname = data.get("uname", "")
            runtime.auth.uid = data.get("mid")

            self.get_user_avatar(data.get("face", ""))

            signal_bus.emit_signal(signal_bus.parse.update_preview_info)

            logger.info("用户信息获取成功，用户名: %s, UID: %s", runtime.auth.uname, runtime.auth.uid)

        else:
            if config.get(config.is_login):
                runtime.auth.is_expired = True

                self.show_toast_error(
                    Translator.ERROR_MESSAGES("LOGIN_EXPIRED"),
                    Translator.ERROR_MESSAGES("LOGIN_EXPIRED_MESSAGE")
                )

                return

            logger.warning("用户未登录，无法获取用户信息")

    @Slot(str)
    def on_get_user_info_error(self, error_message: str):
        # 走到这里的是网络层失败（超时、连接重置），弱网下重试往往第二次就通了。
        # 重试期间保持安静：网络差的时候几十个请求一起超时，每条都弹一次会把屏幕刷满
        if self._schedule_retry():
            return

        self.show_toast_error(Translator.ERROR_MESSAGES("USER_INFO_FAILED"), error_message)

    def get_user_avatar(self, face_url: str):
        if not face_url:
            return

        request = NetworkRequestWorker(face_url, response_type = ResponseType.BYTES)
        request.success.connect(self.on_get_user_avatar_success)
        request.error.connect(self.on_get_user_avatar_error)

        AsyncTask.run(request)

    @Slot(object)
    def on_get_user_avatar_success(self, response: bytes):
        signal_bus.emit_signal(signal_bus.login.update_avatar, response)

    @Slot(str)
    def on_get_user_avatar_error(self, error_message: str):
        self.show_toast_error(Translator.ERROR_MESSAGES("USER_AVATAR_FAILED"), error_message)

    def logout(self):
        params = {
            "biliCSRF": config.get(config.bili_jct)
        }

        url = "https://passport.bilibili.com/login/exit/v2"

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, params = params)
        worker.success.connect(self.on_logout_success)
        worker.error.connect(self.on_logout_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_logout_success(self, response: dict):
        config.set(config.is_login, False)
        runtime.auth.is_expired = False

        config.set(config.bili_jct, "")
        config.set(config.DedeUserID, "")
        config.set(config.DedeUserID__ckMd5, "")
        config.set(config.SESSDATA, "")

    @Slot(str)
    def on_logout_error(self, error_message: str):
        self.show_toast_error(Translator.ERROR_MESSAGES("LOGOUT_FAILED"), error_message)

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "Unknown error")

            self.show_toast_error(Translator.ERROR_MESSAGES("UNKNOWN_ERROR"), message)

            raise RuntimeError(message)

user_manager = UserManager()
