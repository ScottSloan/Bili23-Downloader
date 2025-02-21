import os
import json
import qrcode
import requests
from io import BytesIO
from datetime import datetime

from utils.tool_v2 import RequestTool, UniversalTool
from utils.config import Config, ConfigUtils
from utils.common.enums import StatusCode

class LoginInfo:
    url: str = ""
    qrcode_key: str = ""

    token: str = ""
    challenge: str = ""
    gt: str = ""

    validate: str = ""
    seccode: str = ""

    captcha_key: str = ""

class LoginBase:
    # 登录基类
    def __init__(self, session: requests.sessions.Session):
        self.session = session

    def get_user_info(self, refresh = False):
        url = "https://api.bilibili.com/x/web-interface/nav"

        # 判断是否刷新用户信息
        if refresh:
            headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA)

        else:
            headers = RequestTool.get_headers()
            
            headers["Cookie"] = ";".join([f'{key}={value}' for (key, value) in self.session.cookies.items()])

        req = self.session.get(url, headers = headers, proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        resp = json.loads(req.text)["data"]
                
        return {
            "username": resp["uname"],
            "face_url": resp["face"],
            "login_time": int(datetime.timestamp(datetime.now())),
            "SESSDATA": self.session.cookies["SESSDATA"] if not refresh else Config.User.SESSDATA,
            "DedeUserID": self.session.cookies["DedeUserID"] if not refresh else Config.User.DedeUserID,
            "DedeUserID__ckMd5": self.session.cookies["DedeUserID__ckMd5"] if not refresh else Config.User.DedeUserID__ckMd5,
            "bili_jct": self.session.cookies["bili_jct"] if not refresh else Config.User.bili_jct,
        }

    def logout(self):
        url = "https://passport.bilibili.com/login/exit/v2"

        form = {
            "biliCSRF": Config.User.bili_jct
        }

        self.session.post(url, params = form, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        Config.User.login = False
        Config.User.face_url = Config.User.username = Config.User.SESSDATA = ""

        kwargs = {
            "login": False,
            "face_url": "",
            "username": "",
            "SESSDATA": "",
            "DedeUserID": "",
            "DedeUserID__ckMd5": "",
            "bili_jct": "",
            "timestamp": 0
        }

        utils = ConfigUtils()
        utils.update_config_kwargs(Config.User.user_config_path, "user", **kwargs)

        UniversalTool.remove_files(os.path.dirname(Config.User.user_config_path), ["face.jpg"])

class QRLogin(LoginBase):
    def __init__(self, session):
        LoginBase.__init__(self, session)

    def init_qrcode(self):
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

        req = self.session.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        LoginInfo.url = resp["data"]["url"]
        LoginInfo.qrcode_key = resp["data"]["qrcode_key"]
    
    def get_qrcode(self):
        pic = BytesIO()

        qrcode.make(LoginInfo.url).save(pic)

        return pic.getvalue()
    
    def check_scan(self):
        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={LoginInfo.qrcode_key}"

        req = self.session.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        req_json = json.loads(req.text)

        return {
            "message": req_json["data"]["message"],
            "code": req_json["data"]["code"]}

class SMSLogin(LoginBase):
    def __init__(self, session):
        LoginBase.__init__(self, session)

    def get_country_list(self):
        url = "https://passport.bilibili.com/x/passport-login/web/country"

        req = self.session.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

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

        req = self.session.post(url, params = form, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        data = json.loads(req.text)

        if data["code"]  == StatusCode.Success.value:
            # 只有短信发送成功时才设置 captcha_key
            LoginInfo.captcha_key = data["data"]["captcha_key"]

        return data

    def login(self, tel: int, code: int, cid: int):
        url = "https://passport.bilibili.com/x/passport-login/web/login/sms"

        form = {
            "cid": cid,
            "tel": tel,
            "code": code,
            "source": "main-fe-header",
            "captcha_key": LoginInfo.captcha_key
        }
        
        req = self.session.post(url, params = form, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        data = json.loads(req.text)

        return data

class CaptchaUtils:
    def __init__(self):
        pass

    def get_geetest_challenge_gt(self):
        req = requests.get("https://passport.bilibili.com/x/passport-login/captcha?source=main-fe-header&t=0.1867987009754133", headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        data = json.loads(req.text)

        LoginInfo.token = data["data"]["token"]
        LoginInfo.challenge = data["data"]["geetest"]["challenge"]
        LoginInfo.gt = data["data"]["geetest"]["gt"]
