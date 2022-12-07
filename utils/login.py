import json
import qrcode
import requests
from io import BytesIO 

from .tools import *
from utils.api import API

class QRLoginInfo:
    url = qrcode_key = ""

class QRLogin:
    def __init__(self):
        self.session = requests.session()

    def init_qrcode(self):
        url = API.QRLogin.qrcode_url_api()

        request = self.session.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        login_json = json.loads(request.text)

        QRLoginInfo.url = login_json["data"]["url"]
        QRLoginInfo.qrcode_key = login_json["data"]["qrcode_key"]
    
    def get_qrcode_pic(self):
        pic = BytesIO()

        qrcode.make(QRLoginInfo.url).save(pic)

        return pic.getvalue()
    
    def check_scan(self):
        url = API.QRLogin.qrcode_status_api(QRLoginInfo.qrcode_key)

        req = self.session.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        req_json = json.loads(req.text)

        return {
            "message": req_json["data"]["message"],
            "code": req_json["data"]["code"]}
    
    def get_user_info(self, session = False, cookie = None):
        url = API.QRLogin.user_info_api()

        if session:
            info_requests = self.session.get(url, proxies = get_proxy(), auth = get_auth())
        else:
            info_requests = requests.get(url, headers = get_header(cookie = cookie), proxies = get_proxy(), auth = get_auth())

        info_json = json.loads(info_requests.text)["data"]
                
        user_info = {
            "uid": info_json["mid"],
            "uname": info_json["uname"],
            "face": info_json["face"],
            "level": info_json["level_info"]["current_level"],
            "vip_status": info_json["vipType"],
            "vip_badge": info_json["vip_label"]["img_label_uri_hans_static"],
        }

        user_info["sessdata"] = self.session.cookies["SESSDATA"] if session else cookie

        return user_info
        