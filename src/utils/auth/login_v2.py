import wx
import json
import qrcode
import urllib.parse
from io import BytesIO

from utils.config import Config
from utils.common.request import RequestUtils
from utils.common.enums import StatusCode, Platform
from utils.common.exception import GlobalException
from utils.common.datetime_util import DateTime

from utils.module.pic.face import Face

class LoginInfo:
    class Captcha:
        flag: bool = False

        token: str = ""
        challenge: str = ""
        gt: str = ""

        validate: str = ""
        seccode: str = ""

        captcha_key: str = ""
    
    class QRCode:
        url: str = ""
        key: str = ""

class Login:
    class QRCode:
        @staticmethod
        def generate_qrcode():
            params = {
                "source": "main-fe-header",
                "go_url": "https://www.bilibili.com/",
                "web_location": "333.1007"
            }

            url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/generate?{params}"

            data = Login.request_get(url)

            LoginInfo.QRCode.url = data["data"]["url"]
            LoginInfo.QRCode.key = data["data"]["qrcode_key"]

        @staticmethod
        def get_qrcode_img_io():
            pic = BytesIO()

            qrcode.make(LoginInfo.QRCode.url).save(pic)

            return BytesIO(pic.getvalue())

        @staticmethod
        def check_scan_status():
            url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={LoginInfo.QRCode.key}"

            data = Login.request_get(url)

            Config.Auth.refresh_token = data["data"]["refresh_token"]

            return {
                "message": data["data"]["message"],
                "code": data["data"]["code"]
            }

        @staticmethod
        def get_qrcode_size():
            match Platform(Config.Sys.platform):
                case Platform.Windows | Platform.macOS:
                    size = wx.Size(150, 150) if Config.Sys.dpi_scale_factor <= 1.5 else wx.Size(75, 75)

                case Platform.Linux:
                    size = wx.Size(150, 150)

            factor = Config.Sys.dpi_scale_factor

            return size.Scale(factor, factor)

    class SMS:
        @staticmethod
        def send_sms(tel: int, cid: int):
            url = "https://passport.bilibili.com/x/passport-login/web/sms/send"

            form = {
                "cid": cid,
                "tel": tel,
                "source": "main-fe-header",
                "token": LoginInfo.Captcha.token,
                "challenge": LoginInfo.Captcha.challenge,
                "validate": LoginInfo.Captcha.validate,
                "seccode": LoginInfo.Captcha.seccode
            }

            Login.clear_captcha_info()

            data = Login.request_post(url, params = form)

            LoginInfo.Captcha.captcha_key = data["data"]["captcha_key"]

            return data

        @staticmethod
        def login(tel: int, cid: int, validate_code: int):
            url = "https://passport.bilibili.com/x/passport-login/web/login/sms"

            form = {
                "cid": cid,
                "tel": tel,
                "code": validate_code,
                "source": "main-fe-header",
                "captcha_key": LoginInfo.Captcha.captcha_key,
                "go_url": "https://www.bilibili.com/"
            }

            data = Login.request_post(url, params = form)

            Config.Auth.refresh_token = data["data"]["refresh_token"]

            return data

    class Captcha:
        @staticmethod
        def get_geetest_challenge_gt():
            url = "https://passport.bilibili.com/x/passport-login/captcha?source=main-fe-header&t=0.1867987009754133"

            data = Login.request_get(url)

            LoginInfo.Captcha.token = data["data"]["token"]
            LoginInfo.Captcha.challenge = data["data"]["geetest"]["challenge"]
            LoginInfo.Captcha.gt = data["data"]["geetest"]["gt"]

    @classmethod
    def request_get(cls, url: str, headers: dict = None):
        if not headers:
            headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA)

        try:
            req = RequestUtils.request_get(url, headers = headers)

        except Exception as e:
            raise GlobalException(callback = cls.on_error) from e

        data = json.loads(req.text)

        cls.check_json(data)

        return data
    
    @classmethod
    def request_post(cls, url: str, headers: dict = None, params = None, check: bool = True):
        if not headers:
            headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA)

        try:
            req = RequestUtils.request_post(url, headers = headers, params = params)

        except Exception as e:
            raise GlobalException(callback = cls.on_error) from e

        data = json.loads(req.text)

        if check:
            cls.check_json(data)

        return data

    @classmethod
    def get_user_info(cls, login = True):
        url = "https://api.bilibili.com/x/web-interface/nav"

        if login:
            headers = RequestUtils.get_headers()
            
            headers["Cookie"] = ";".join([f'{key}={value}' for (key, value) in RequestUtils.session.cookies.items()])
        else:
            headers = None

        data = cls.request_get(url, headers = headers).get("data")

        if login:
            info = {
                "username": data.get("uname"),
                "face_url": data.get("face"),
                "SESSDATA": RequestUtils.session.cookies.get("SESSDATA"),
                "DedeUserID": RequestUtils.session.cookies.get("DedeUserID"),
                "DedeUserID__ckMd5": RequestUtils.session.cookies.get("DedeUserID__ckMd5"),
                "bili_jct": RequestUtils.session.cookies.get("bili_jct"),
            }

            if login:
                info["login_expires"] = DateTime.get_timedelta(DateTime.now(), 365)

            return info
        else:
            return {
                "username": data.get("uname"),
                "face_url": data.get("face"),
            }

    @classmethod
    def login(cls, info: dict):
        cls.check_cookie(info)

        Config.User.login = True
        Config.User.face_url = info.get("face_url") + "@.jpg"
        Config.User.username = info.get("username")
        Config.User.SESSDATA = info.get("SESSDATA")
        Config.User.DedeUserID = info.get("DedeUserID")
        Config.User.DedeUserID__ckMd5 = info.get("DedeUserID__ckMd5")
        Config.User.bili_jct = info.get("bili_jct")

        if "login_expires" in info:
            Config.User.login_expires = info.get("login_expires")

        Config.save_user_config()

        cls.on_login_success()
    
    @classmethod
    def logout(cls):
        url = "https://passport.bilibili.com/login/exit/v2"

        form = {
            "biliCSRF": Config.User.bili_jct
        }

        cls.request_post(url, params = form, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA), check = False)

        cls.clear_login_info()

    @classmethod
    def refresh(cls):
        info = cls.get_user_info(login = False)

        Config.User.face_url = info["face_url"] + "@.jpg"
        Config.User.username = info["username"]

        Face.remove()

    @classmethod
    def on_login_success(cls):
        from utils.auth.cookie import Utils
        from utils.common.data.exclimbwuzhi import ex_data

        correspond_path = Utils.get_correspond_path()

        Utils.exclimbwuzhi(ex_data[4], correspond_path)

    @staticmethod
    def clear_login_info():
        Config.User.login = False
        Config.User.face_url = ""
        Config.User.username = ""
        Config.User.login_expires = 0
        Config.User.SESSDATA = ""
        Config.User.DedeUserID = ""
        Config.User.DedeUserID__ckMd5 = ""
        Config.User.bili_jct = ""

        Config.save_user_config()

        Face.remove()

    @staticmethod
    def clear_captcha_info():
        LoginInfo.Captcha.challenge = ""
        LoginInfo.Captcha.gt = ""

        LoginInfo.Captcha.seccode = ""
        LoginInfo.Captcha.validate = ""

        LoginInfo.Captcha.captcha_key = ""

    @classmethod
    def check_json(cls, data: dict):
        if data.get("code") != StatusCode.Success.value:
            raise GlobalException(message = data.get("message"), code = data.get("code"), callback = cls.on_error, json_data = data)

    @classmethod
    def check_cookie(cls, cookie: dict):
        for key, value in cookie.items():
            if not value:
                raise GlobalException(message = f"Cookie 字段 {key} 无效：{value}", callback = cls.on_error, json_data = cookie)

    @classmethod
    def set_on_error_callback(cls, callback):
        cls.on_error = callback

    @staticmethod
    def url_encode(params: dict):
        return urllib.parse.urlencode(params)