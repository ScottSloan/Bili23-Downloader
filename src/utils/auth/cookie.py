import json
import requests

from utils.tool_v2 import RequestTool
from utils.config import Config

class CookieUtils:
    def checkCookieInfo():
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        return resp["data"]["refresh"]