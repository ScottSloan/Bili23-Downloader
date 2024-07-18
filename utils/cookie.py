import json
import requests

from utils.tools import *

class CookieUtils:
    def checkCookieInfo():
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"

        req = requests.get(url, headers = get_header(cookie = Config.User.sessdata), auth = get_auth(), proxies = get_proxy())
        resp = json.loads(req.text)

        return resp["data"]["refresh"]