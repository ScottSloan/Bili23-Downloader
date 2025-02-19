import json
import hmac
import time
import random
import hashlib
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait

from utils.tool_v2 import RequestTool
from utils.config import Config, utils

class CookieUtils:
    def checkCookieInfo():
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        return resp["data"]["refresh"]
    
    def init_cookie_params():
        def _generate():
            Config.Auth.c_time = int(time.time())

            CookieUtils.gen_uuid()
            CookieUtils.gen_b_lsid()

            task = []

            thread_pool = ThreadPoolExecutor(max_workers = 3)
            task.append(thread_pool.submit(CookieUtils.get_buvid3))
            task.append(thread_pool.submit(CookieUtils.get_bili_ticket))
            task.append(thread_pool.submit(CookieUtils.get_buvid4))

            wait(task)

            kwargs = {
                "c_time": Config.Auth.c_time,
                "buvid3": Config.Auth.buvid3,
                "buvid4": Config.Auth.buvid4,
                "b_nut": Config.Auth.b_nut,
                "bili_ticket": Config.Auth.bili_ticket,
                "uuid": Config.Auth.uuid,
                "b_lsid": Config.Auth.b_lsid
            }

            utils.update_config_kwargs(Config.User.user_config_path, "cookie_params", **kwargs)

        if Config.Auth.c_time:
            today = datetime.now().date()
            timestamp = datetime.fromtimestamp(int(Config.Auth.c_time)).date()

            if not (today == timestamp):
                _generate()
        else:
            _generate()

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

        Config.Auth.bili_ticket = data["data"]["ticket"]
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