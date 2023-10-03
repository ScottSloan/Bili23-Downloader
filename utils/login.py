import json
import qrcode
import requests
from io import BytesIO

from .tools import *
from .config import Config, conf

class QRLoginInfo:
    url = qrcode_key = None

class QRLogin:
    def __init__(self):
        pass

    def init_qrcode(self):
        self.session = requests.session()

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
            req = self.session.get(url, proxies = get_proxy(), auth = get_auth())

        resp = json.loads(req.text)["data"]
                
        return {
            "uname": resp["uname"],
            "face": resp["face"],
            "sessdata": self.session.cookies["SESSDATA"] if not refresh else Config.User.sessdata
        }

    def logout(self):
        Config.User.login = False
        Config.User.face = Config.User.uname = Config.User.sessdata = ""

        conf.config.set("user", "login", str(int(Config.User.login)))
        conf.config.set("user", "face", Config.User.face)
        conf.config.set("user", "uname", Config.User.uname)
        conf.config.set("user", "sessdata", Config.User.sessdata)

        conf.save()