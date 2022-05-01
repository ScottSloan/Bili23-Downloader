import json
import qrcode
import requests
from io import BytesIO 

from utils.tools import get_header, get_proxy

class LoginInfo:
    url = oauthKey = ""

class Login:
    def __init__(self):
        self.session = requests.session()

        self.init_qrcode()

    @property
    def get_qrcode_url(self):
        return "https://passport.bilibili.com/qrcode/getLoginUrl"

    @property
    def get_login_info_url(self):
        return "https://passport.bilibili.com/qrcode/getLoginInfo"

    @property
    def get_user_info_url(self):
        return "https://api.live.bilibili.com/User/getUserInfo"

    def init_qrcode(self):
        req = self.session.get(self.get_qrcode_url, headers = get_header(), proxies = get_proxy())
        login_json = json.loads(req.text)

        LoginInfo.url = login_json["data"]["url"]
        LoginInfo.oauthKey = login_json["data"]["oauthKey"]
    
    def get_qrcode_pic(self):
        pic = BytesIO()

        img = qrcode.make(LoginInfo.url)
        img.save(pic)

        return pic.getvalue()
    
    def check_isscan(self) -> bool:
        data = {'oauthKey':LoginInfo.oauthKey, "gourl":"https://passport.bilibili.com/account/security"}

        req = self.session.post(self.get_login_info_url, data = data, headers = get_header(), proxies = get_proxy())
        req_json = json.loads(req.text)

        return [req_json["status"], req_json["data"] if not req_json["status"] else 0]
    
    def get_user_info(self) -> dict:
        req = self.session.get(self.get_user_info_url, proxies = get_proxy())
        req_json = json.loads(req.text)

        data_json = req_json["data"]

        uuid = data_json["uid"]
        uname = data_json["uname"]
        face = data_json["face"]

        vip = True if data_json["vip"] != 0 and data_json["svip"] != 0 else False

        return {"uuid":uuid, "uname":uname, "face":face, "vip":vip, "sessdata":self.session.cookies["SESSDATA"]}