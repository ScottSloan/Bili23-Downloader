import wx
import json
import qrcode
from io import BytesIO
from datetime import datetime, timedelta

from utils.config import Config, user_config_group

from utils.module.pic.face import Face

from utils.common.request import RequestUtils
from utils.common.enums import StatusCode, Platform
from utils.common.exception import GlobalException

class LoginInfo:
    class Captcha:
        flag: bool = False
        
        token: str = ""
        challenge: str = ""
        gt: str = ""

        validate: str = ""
        seccode: str = ""

        captcha_key: str = ""

    url: str = ""
    qrcode_key: str = ""

class Login:
    class QRCode:
        @staticmethod
        def generate_qrcode():
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

            data = Login.request_get(url)

            LoginInfo.url = data["data"]["url"]
            LoginInfo.qrcode_key = data["data"]["qrcode_key"]

        @staticmethod
        def get_qrcode_img_io():
            pic = BytesIO()

            qrcode.make(LoginInfo.url).save(pic)

            return BytesIO(pic.getvalue())

        @staticmethod
        def check_scan_status():
            url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={LoginInfo.qrcode_key}"

            data = Login.request_get(url)

            return {
                "message": data["data"]["message"],
                "code": data["data"]["code"]
            }

        @staticmethod
        def get_qrcode_size():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    size = wx.Size(150, 150) if Config.Sys.dpi_scale_factor <= 1.5 else wx.Size(75, 75)

                case Platform.Linux | Platform.macOS:
                    size = wx.Size(150, 150)

            factor = Config.Sys.dpi_scale_factor

            return size.Scale(factor, factor)

    class SMS:
        @staticmethod
        def get_country_list():
            url = "https://passport.bilibili.com/x/passport-login/web/country"

            return Login.request_get(url)["data"]["list"]

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
        def login():
            pass

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

        req = RequestUtils.request_get(url, headers = headers)

        data = json.loads(req.text)

        cls.check_json(data)

        return data
    
    @classmethod
    def request_post(cls, url: str, headers: dict = None, params = None):
        if not headers:
            headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA)

        req = RequestUtils.request_post(url, headers = headers, params = params)

        data = json.loads(req.text)

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
                "username": data["uname"],
                "face_url": data["face"],
                "SESSDATA": RequestUtils.session.cookies["SESSDATA"],
                "DedeUserID": RequestUtils.session.cookies["DedeUserID"],
                "DedeUserID__ckMd5": RequestUtils.session.cookies["DedeUserID__ckMd5"],
                "bili_jct": RequestUtils.session.cookies["bili_jct"],
            }

            if login:
                info["login_expires"] = int((datetime.now() + timedelta(days = 365)).timestamp())

            return info
        else:
            return {
                "username": data["uname"],
                "face_url": data["face"],
            }

    @staticmethod
    def login(info: dict):
        Config.User.login = True
        Config.User.face_url = info.get("face_url") + "@.jpg"
        Config.User.username = info.get("username")
        Config.User.SESSDATA = info.get("SESSDATA")
        Config.User.DedeUserID = info.get("DedeUserID")
        Config.User.DedeUserID__ckMd5 = info.get("DedeUserID__ckMd5")
        Config.User.bili_jct = info.get("bili_jct")

        if "login_expires" in info:
            Config.User.login_expires = info.get("login_expires")

        Config.save_config_group(Config, user_config_group, Config.User.user_config_path)
    
    @classmethod
    def logout(cls):
        url = "https://passport.bilibili.com/login/exit/v2"

        form = {
            "biliCSRF": Config.User.bili_jct
        }

        cls.request_post(url, params = form, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        cls.clear_login_info()

    @classmethod
    def refresh(cls):
        info = cls.get_user_info(login = False)

        Config.User.face_url = info["face_url"] + "@.jpg"
        Config.User.username = info["username"]

        Face.remove()

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

        Config.save_config_group(Config, user_config_group, Config.User.user_config_path)

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
    def set_on_error_callback(cls, callback):
        cls.on_error = callback