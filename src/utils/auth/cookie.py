import json
import hmac
import time
import random
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor

from utils.tool_v2 import RequestTool
from utils.config import Config

class CookieUtils:
    def checkCookieInfo():
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata))
        resp = json.loads(req.text)

        return resp["data"]["refresh"]
    
    def init_cookie_params():
        CookieUtils.gen_uuid()
        CookieUtils.gen_b_lsid()

        thread_pool = ThreadPoolExecutor(max_workers = 3)
        thread_pool.submit(CookieUtils.get_buvid3)
        thread_pool.submit(CookieUtils.get_bili_ticket)
        thread_pool.submit(CookieUtils.get_buvid4)

    def get_bili_ticket():
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

    def get_buvid4():
        url = "https://api.bilibili.com/x/frontend/finger/spi"

        req = RequestTool.request_get(url)
        data = json.loads(req.text)

        Config.Auth.buvid4 = data["data"]["b_4"]

    def gen_uuid():
        t = CookieUtils.get_timestamp() % 100000
        mp = list("123456789ABCDEF") + ["10"]
        pck = [8, 4, 4, 4, 12]

        gen_part = lambda x: "".join([random.choice(mp) for _ in range(x)])  # noqa: E731

        Config.Auth.uuid = "-".join([gen_part(l) for l in pck]) + str(t).ljust(5, "0") + "infoc"  # noqa: E741

    def gen_b_lsid():
        ret = ""

        for _ in range(8):
            ret += hex(random.randint(0, 15))[2:].upper()

        ret = f"{ret}_{hex(CookieUtils.get_timestamp())[2:].upper()}"

        Config.Auth.b_lsid = ret

    def get_timestamp():
        return int(time.time() * 1000)