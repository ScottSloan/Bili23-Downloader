import json
import qrcode
import requests
from io import BytesIO

from utils.tools import get_header, get_proxy, get_auth
from utils.config import Config, conf

class QRLoginInfo:
    url = qrcode_key = None

class PasswordLoginInfo:
    hash: str = ""
    key: str = ""

class CaptchaInfo:
    token: str = ""
    challenge: str = ""
    gt: str = ""

    validate: str = ""
    seccode: str = ""

class QRLogin:
    def __init__(self):
        pass

    def init_qrcode(self):
        self.session = requests.sessions.session()

        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

        req = self.session.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        resp = json.loads(req.text)

        QRLoginInfo.url = resp["data"]["url"]
        QRLoginInfo.qrcode_key = resp["data"]["qrcode_key"]
    
    def get_qrcode(self):
        pic = BytesIO()

        qrcode.make(QRLoginInfo.url).save(pic)

        return pic.getvalue()
    
    def check_scan(self):
        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={QRLoginInfo.qrcode_key}"

        req = self.session.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        req_json = json.loads(req.text)

        return {
            "message": req_json["data"]["message"],
            "code": req_json["data"]["code"]}

    def get_user_info(self, refresh = False):
        url = "https://api.bilibili.com/x/web-interface/nav"

        if refresh:
            req = requests.get(url, headers = get_header(cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth())
        else:
            former_headers = get_header()
            
            former_headers["Cookie"] = ";".join([f'{key}={value}' for (key, value) in self.session.cookies.items()])

            req = self.session.get(url, headers = former_headers, proxies = get_proxy(), auth = get_auth())

        resp = json.loads(req.text)["data"]
                
        return {
            "uname": resp["uname"],
            "face": resp["face"],
            "sessdata": self.session.cookies["SESSDATA"] if not refresh else Config.User.sessdata
        }

    def logout(self):
        Config.User.login = False
        Config.User.face = Config.User.uname = Config.User.sessdata = ""

        conf.save_all_user_config()

class PasswordLogin:
    def __init__(self):
        self.session = requests.sessions.session()

    def get_public_key(self):
        url = "https://passport.bilibili.com/x/passport-login/web/key"

        req = self.session.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        data = json.loads(req.text)

        PasswordLoginInfo.hash = data["data"]["hash"]
        PasswordLoginInfo.key = data["data"]["key"]

    def login(self):
        url = "https://passport.bilibili.com/x/passport-login/web/login"

        req = self.session.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        data = json.loads(req.text)

        print(data)

class Captcha:
    def __init__(self):
        pass

    def get_geetest_challenge_gt(self):
        req = requests.get("https://passport.bilibili.com/x/passport-login/captcha?source=main_web", headers = get_header(), proxies = get_proxy(), auth = get_auth())

        data = json.loads(req.text)

        CaptchaInfo.token = data["data"]["token"]
        CaptchaInfo.challenge = data["data"]["geetest"]["challenge"]
        CaptchaInfo.gt = data["data"]["geetest"]["gt"]
