from util.network.request import NetworkRequestWorker, RequestType, update_cookies

from util.common import get_timestamp, get_timestamp_next_day, config
from util.thread import AsyncTask
from util.auth import AuthBase

import hashlib
import random
import hmac

class CookieManager(AuthBase):
    def __init__(self):
        super().__init__()

    def init_cookie_info(self):
        self.get_buvid()
        self.get_bili_ticket()

    def get_buvid(self):
        def on_success(response: dict):
            self.check_response(response)

            config.set(config.buvid3, response["data"]["b_3"])
            config.set(config.buvid4, response["data"]["b_4"])
            config.set(config.buvid_expires, get_timestamp_next_day())

            self.get_uuid()
            self.get_b_lsid()
            self.get_b_nut()

            update_cookies()

        def on_error(error_message: str):
            self.show_toast_error("获取 buvid 失败", error_message)

        if get_timestamp() < config.get(config.buvid_expires):
            return

        url = "https://api.bilibili.com/x/frontend/finger/spi"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    def get_bili_ticket(self):
        def on_success(response: dict):
            self.check_response(response)

            config.set(config.bili_ticket, response["data"]["ticket"])
            config.set(config.bili_ticket_expires, self.timedelta_3_days())

            update_cookies()

        def on_error(error_message: str):
            self.show_toast_error("获取 bili_ticket 失败", error_message)

        if get_timestamp() < config.get(config.bili_ticket_expires):
            return

        url = "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"

        params = {
            "key_id": "ec02",
            "hexsign": self.hmac_sha256("XgwSnGZ1p", f"ts{get_timestamp()}"),
            "context[ts]": f"{get_timestamp()}",
            "csrf": config.get(config.bili_jct)
        }

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, params = params)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    def get_uuid(self):
        t = get_timestamp() % 100000
        mp = list("123456789ABCDEF") + ["10"]
        pck = [8, 4, 4, 4, 12]

        gen_part = lambda x: "".join([random.choice(mp) for _ in range(x)])

        config.set(config.uuid, "-".join([gen_part(l) for l in pck]) + str(t).ljust(5, "0") + "infoc")

    def get_b_lsid(self):
        ret = ""

        for _ in range(8):
            ret += hex(random.randint(0, 15))[2:].upper()

        ret = f"{ret}_{hex(get_timestamp())[2:].upper()}"

        config.set(config.b_lsid, ret)

    def get_b_nut(self):
        config.set(config.b_nut, get_timestamp())

    def hmac_sha256(self, key: str, message: str):
        key = key.encode("utf-8")
        message = message.encode("utf-8")

        hmac_obj = hmac.new(key, message, hashlib.sha256)

        return hmac_obj.digest().hex()
    
    def timedelta_3_days(self):
        return get_timestamp() + 3 * 24 * 3600

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "未知错误")

            self.show_toast_error("错误", message)

            raise Exception(message)
        
cookie_manager = CookieManager()
