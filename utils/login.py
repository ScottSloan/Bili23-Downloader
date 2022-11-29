import json
import qrcode
import requests
from io import BytesIO 

from .tools import *
from .config import Config

class LoginInfo:
    url = qrcode_key = ""

class Login:
    def __init__(self):
        self.session = requests.session()

        self.init_qrcode()

    @property
    def get_qrcode_url(self):
        return "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

    @property
    def scan_qrcode_url(self):
        return "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"

    @property
    def user_info_url(self):
        return "https://api.live.bilibili.com/User/getUserInfo"

    @property
    def user_detail_info_url(self):
        return "https://api.bilibili.com/x/space/acc/info?mid=" + Config.user_uid

    def init_qrcode(self):
        req = self.session.get(self.get_qrcode_url, headers = get_header(), proxies = get_proxy())
        login_json = json.loads(req.text)

        LoginInfo.url = login_json["data"]["url"]
        LoginInfo.qrcode_key = login_json["data"]["qrcode_key"]
    
    def get_qrcode_pic(self):
        pic = BytesIO()

        qrcode.make(LoginInfo.url).save(pic)

        return pic.getvalue()
    
    def check_scan(self):
        url = self.scan_qrcode_url + "?qrcode_key=" + LoginInfo.qrcode_key

        req = self.session.get(url, headers = get_header(), proxies = get_proxy())
        req_json = json.loads(req.text)

        return {
            "message": req_json["data"]["message"],
            "code": req_json["data"]["code"]}
    
    def get_user_info(self) -> dict:
        info_requests = self.session.get(self.user_info_url, proxies = get_proxy())
        info_json = json.loads(info_requests.text)["data"]
                
        Config.user_uid = str(info_json["uid"])

        detail_request = self.session.get(self.user_detail_info_url, headers = get_header(), proxies = get_proxy())
        detail_json = json.loads(detail_request.text)["data"]
        
        return {
            "uid": info_json["uid"],
            "uname": info_json["uname"],
            "face": info_json["face"],
            "level": detail_json["level"],
            "sessdata": self.session.cookies["SESSDATA"]
        }
        