import json
import qrcode
import requests
from io import BytesIO
from datetime import datetime, timedelta

from utils.tool_v2 import UniversalTool
from utils.config import Config, user_config_group

from utils.common.enums import StatusCode
from utils.common.request import RequestUtils

from utils.module.pic.face import Face

class LoginInfo:
    url: str = ""
    qrcode_key: str = ""

    token: str = ""
    challenge: str = ""
    gt: str = ""

    validate: str = ""
    seccode: str = ""

    captcha_key: str = ""

class Login:
    def __init__(self):
        pass

    def init_session(self):
        self.session = requests.sessions.Session()

    def get_user_info(self, refresh = False):
        url = "https://api.bilibili.com/x/web-interface/nav"

        if refresh:
            headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA)

        else:
            headers = RequestUtils.get_headers()
            
            headers["Cookie"] = ";".join([f'{key}={value}' for (key, value) in self.session.cookies.items()])

        req = self.session.get(url, headers = headers, proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())

        resp = json.loads(req.text)["data"]
                
        return {
            "username": resp["uname"],
            "face_url": resp["face"],
            "login_expires": int((datetime.now() + timedelta(days = 365)).timestamp()),
            "SESSDATA": self.session.cookies["SESSDATA"] if not refresh else Config.User.SESSDATA,
            "DedeUserID": self.session.cookies["DedeUserID"] if not refresh else Config.User.DedeUserID,
            "DedeUserID__ckMd5": self.session.cookies["DedeUserID__ckMd5"] if not refresh else Config.User.DedeUserID__ckMd5,
            "bili_jct": self.session.cookies["bili_jct"] if not refresh else Config.User.bili_jct,
        }

    def refresh(self):
        self.init_session()

        user_info = self.get_user_info(refresh = True)

        Config.User.face_url = user_info["face_url"] + "@.jpg"
        Config.User.username = user_info["username"]

        UniversalTool.remove_files([Config.User.face_path])

    def logout(self):
        self.init_session()

        url = "https://passport.bilibili.com/login/exit/v2"

        form = {
            "biliCSRF": Config.User.bili_jct
        }

        self.session.post(url, params = form, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())

        Config.User.login = False
        Config.User.face_url = ""
        Config.User.username = ""
        Config.User.login_expires = 0
        Config.User.SESSDATA = ""
        Config.User.DedeUserID = ""
        Config.User.DedeUserID__ckMd5 = ""
        Config.User.bili_jct = ""

        Config.save_config_group(Config, user_config_group, Config.User.user_config_path)

        UniversalTool.remove_files([Config.User.face_path])

    def login(self, info: dict):
        Config.User.login = True
        Config.User.face_url = info["face_url"] + "@.jpg"
        Config.User.username = info["username"]
        Config.User.login_expires = int((datetime.now() + timedelta(days = 365)).timestamp())
        Config.User.SESSDATA = info["SESSDATA"]
        Config.User.DedeUserID = info["DedeUserID"]
        Config.User.DedeUserID__ckMd5 = info["DedeUserID__ckMd5"]
        Config.User.bili_jct = info["bili_jct"]

        Config.save_config_group(Config, user_config_group, Config.User.user_config_path)

        Face.check_face_path()

class QRLogin(Login):
    def __init__(self):
        Login.__init__(self)

    def init_qrcode(self):
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

        req = self.session.get(url, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())
        resp = json.loads(req.text)

        LoginInfo.url = resp["data"]["url"]
        LoginInfo.qrcode_key = resp["data"]["qrcode_key"]
    
    def get_qrcode(self):
        pic = BytesIO()

        qrcode.make(LoginInfo.url).save(pic)

        return pic.getvalue()
    
    def check_scan(self):
        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={LoginInfo.qrcode_key}"

        req = self.session.get(url, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())
        req_json = json.loads(req.text)

        return {
            "message": req_json["data"]["message"],
            "code": req_json["data"]["code"]}

class SMSLogin(Login):
    def __init__(self):
        Login.__init__(self)

    def get_country_list(self):
        url = "https://passport.bilibili.com/x/passport-login/web/country?web_location=333.1007"

        req = self.session.get(url, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())

        data = json.loads(req.text)

        return data

    def send_sms(self, tel: int, cid: int):
        url = "https://passport.bilibili.com/x/passport-login/web/sms/send"

        form = {
            "cid": cid,
            "tel": tel,
            "source": "main-fe-header",
            "token": LoginInfo.token,
            "challenge": LoginInfo.challenge,
            "validate": LoginInfo.validate,
            "seccode": LoginInfo.seccode
        }

        req = self.session.post(url, params = form, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())
        data = json.loads(req.text)

        if data["code"]  == StatusCode.Success.value:
            # 只有短信发送成功时才设置 captcha_key
            LoginInfo.captcha_key = data["data"]["captcha_key"]

        return data

    def sms_login(self, tel: int, code: int, cid: int):
        url = "https://passport.bilibili.com/x/passport-login/web/login/sms"

        form = {
            "cid": cid,
            "tel": tel,
            "code": code,
            "source": "main-fe-header",
            "captcha_key": LoginInfo.captcha_key
        }
        
        req = self.session.post(url, params = form, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())
        data = json.loads(req.text)

        return data

class CaptchaUtils:
    def __init__(self):
        pass

    def get_geetest_challenge_gt(self):
        req = requests.get("https://passport.bilibili.com/x/passport-login/captcha?source=main-fe-header&t=0.1867987009754133", headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())

        data = json.loads(req.text)

        LoginInfo.token = data["data"]["token"]
        LoginInfo.challenge = data["data"]["geetest"]["challenge"]
        LoginInfo.gt = data["data"]["geetest"]["gt"]
