from util.network import NetworkRequestWorker, RequestType, update_cookies

from util.common import get_timestamp, get_timestamp_next_day, config
from util.common.data import get_exclimbwuzhi_payload
from util.thread import AsyncTask

from .base import AuthBase

import hashlib
import random
import struct
import hmac
import io

class CookieManager(AuthBase):
    def __init__(self):
        super().__init__()

    def init_cookie_info(self):
        self.get_buvid()
        self.get_bili_ticket()

        self.exclimbwuzhi()

    def get_buvid(self):
        def on_success(response: dict):
            self.check_response(response)

            config.set(config.buvid3, response["data"]["b_3"])
            config.set(config.buvid4, response["data"]["b_4"])
            config.set(config.buvid_expires, get_timestamp_next_day())

            self.get_uuid()
            self.get_b_lsid()
            self.get_b_nut()
            self.get_buvid_fp(config.get(config.user_agent), 31)

            update_cookies()

            self.exclimbwuzhi()

        def on_error(error_message: str):
            self.show_toast_error("获取 buvid 失败", error_message)

        if get_timestamp() < config.get(config.buvid_expires):
            return True

        url = "https://api.bilibili.com/x/frontend/finger/spi"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    def get_buvid_fp(self, key: str, seed: int):
        def rotate_left(x: int, k: int):
            bin_str = bin(x)[2:].rjust(64, "0")

            return int(bin_str[k:] + bin_str[:k], base = 2)

        def murmur3_x64_128(source: io.BufferedIOBase, seed: int):
            C1 = 0x87C3_7B91_1142_53D5
            C2 = 0x4CF5_AD43_2745_937F
            C3 = 0x52DC_E729
            C4 = 0x3849_5AB5
            R1, R2, R3, M = 27, 31, 33, 5
            h1, h2 = seed, seed
            processed = 0

            while 1:
                read = source.read(16)
                processed += len(read)

                if len(read) == 16:
                    k1 = struct.unpack("<q", read[:8])[0]
                    k2 = struct.unpack("<q", read[8:])[0]
                    h1 ^= (rotate_left(k1 * C1 % MOD, R2) * C2 % MOD)
                    h1 = ((rotate_left(h1, R1) + h2) * M + C3) % MOD
                    h2 ^= rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
                    h2 = ((rotate_left(h2, R2) + h1) * M + C4) % MOD

                elif len(read) == 0:
                    h1 ^= processed
                    h2 ^= processed
                    h1 = (h1 + h2) % MOD
                    h2 = (h2 + h1) % MOD
                    h1 = fmix64(h1)
                    h2 = fmix64(h2)
                    h1 = (h1 + h2) % MOD
                    h2 = (h2 + h1) % MOD
                    return (h2 << 64) | h1
                
                else:
                    k1 = 0
                    k2 = 0

                    if len(read) >= 15:
                        k2 ^= int(read[14]) << 48
                    if len(read) >= 14:
                        k2 ^= int(read[13]) << 40
                    if len(read) >= 13:
                        k2 ^= int(read[12]) << 32
                    if len(read) >= 12:
                        k2 ^= int(read[11]) << 24
                    if len(read) >= 11:
                        k2 ^= int(read[10]) << 16
                    if len(read) >= 10:
                        k2 ^= int(read[9]) << 8
                    if len(read) >= 9:
                        k2 ^= int(read[8])
                        k2 = rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
                        h2 ^= k2
                    if len(read) >= 8:
                        k1 ^= int(read[7]) << 56
                    if len(read) >= 7:
                        k1 ^= int(read[6]) << 48
                    if len(read) >= 6:
                        k1 ^= int(read[5]) << 40
                    if len(read) >= 5:
                        k1 ^= int(read[4]) << 32
                    if len(read) >= 4:
                        k1 ^= int(read[3]) << 24
                    if len(read) >= 3:
                        k1 ^= int(read[2]) << 16
                    if len(read) >= 2:
                        k1 ^= int(read[1]) << 8
                    if len(read) >= 1:
                        k1 ^= int(read[0])
                    k1 = rotate_left(k1 * C1 % MOD, R2) * C2 % MOD
                    h1 ^= k1

        def fmix64(k: int) -> int:
            C1 = 0xFF51_AFD7_ED55_8CCD
            C2 = 0xC4CE_B9FE_1A85_EC53
            R = 33
            tmp = k
            tmp ^= tmp >> R
            tmp = tmp * C1 % MOD
            tmp ^= tmp >> R
            tmp = tmp * C2 % MOD
            tmp ^= tmp >> R
            return tmp

        MOD = 1 << 64

        source = io.BytesIO(bytes(key, "ascii"))
        m = murmur3_x64_128(source, seed)

        config.set(config.buvid_fp, "{}{}".format(hex(m & (MOD - 1))[2:], hex(m >> 64)[2:]))

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

    def exclimbwuzhi(self):
        def on_success(response: dict):
            code = response.get("code")

            if code != 0:
                on_error(code)

        def on_error(error_message: str):
            self.show_toast_error("请求 ExClimbWuzhi 失败", error_message)

        # 用于激活 buvid3
        url = "https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi"

        payload = get_exclimbwuzhi_payload(
            config.get(config.user_agent),
            config.get(config.uuid)
        )

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, data = payload, content_type = "application/json")
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

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
        
    def format_dict(self, template: dict, context: dict):
        return {
            key: value.format(**context) if isinstance(value, str) and key != "54ef" else value
            for key, value in template.items()
        }
    
cookie_manager = CookieManager()
