import json
import hmac
import time
import hashlib
import requests

from utils.tool_v2 import RequestTool
from utils.config import Config

class CookieInfo:
    ticket = ""

class CookieUtils:
    def checkCookieInfo():
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata))
        resp = json.loads(req.text)

        return resp["data"]["refresh"]
    
    def init_cookie_params():
        CookieUtils.get_buvid3()
        
        CookieUtils.gen_bili_ticket()
    
    def gen_bili_ticket():
        def hmac_sha256(key: str, message: str):
            key = key.encode("utf-8")
            message = message.encode("utf-8")

            hmac_obj = hmac.new(key, message, hashlib.sha256)

            return hmac_obj.digest().hex()

        url = "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"

        params = {
            "key_id": "ec02",
            "hexsign": hmac_sha256("XgwSnGZ1p", f"ts{int(time.time())}"),
            "context[ts]": f"{int(time.time())}",
            "csrf": ""
        }

        req = RequestTool.request_post(url, headers = RequestTool.get_headers(), params = params)
        data = json.loads(req.text)

        img_url: str = data['data']['nav']['img']
        sub_url: str = data['data']['nav']['sub']

        Config.Auth.ticket = data["data"]["ticket"]
        Config.Auth.img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        Config.Auth.sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    
    def get_buvid3():
        url = "https://www.bilibili.com"

        req = RequestTool.request_get(url)

        cookie = requests.utils.dict_from_cookiejar(req.cookies)

        Config.Auth.buvid3 = cookie["buvid3"]
        Config.Auth.b_nut = cookie["b_nut"]