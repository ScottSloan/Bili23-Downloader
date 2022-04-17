import json
import qrcode
import requests
from utils.tools import get_header, get_proxy

class LoginInfo:
    url = oauthKey = ""

class Login:
    def __init__(self):
        self.session = requests.session()

        self.init_qrcode()
        self.get_qrcode_pic()

    @property
    def get_qrcode_url(self):
        return "https://passport.bilibili.com/qrcode/getLoginUrl"

    @property
    def get_login_info_url(self):
        return "https://passport.bilibili.com/qrcode/getLoginInfo"

    def init_qrcode(self):
        req = self.session.get(self.get_qrcode_url, headers = get_header(), proxies = get_proxy())
        login_json = json.loads(req.text)

        LoginInfo.url = login_json["data"]["url"]
        LoginInfo.oauthKey = login_json["data"]["oauthKey"]
    
    def get_qrcode_pic(self):
        img = qrcode.make(LoginInfo.url)
        img.save("qrcode.png")
    
    def check_isscan(self) -> bool:
        data = {'oauthKey':LoginInfo.oauthKey, "gourl":"https://passport.bilibili.com/account/security"}

        req = self.session.post(self.get_login_info_url, data = data, headers = get_header(), proxies = get_proxy())
        rpse_json = json.loads(req.text)

        return [rpse_json["status"], rpse_json["data"] if not rpse_json["status"] else 0, self.session.cookies]