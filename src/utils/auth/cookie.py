import json
import hmac
import time
import hashlib

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
    
    @staticmethod
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