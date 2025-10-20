import io
import json
import time
import hmac
import random
import struct
import hashlib
import binascii
import urllib.parse
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

from utils.config import Config
from utils.auth.login_v2 import Login

from utils.common.request import RequestUtils
from utils.common.datetime_util import DateTime
from utils.common.data.rsa_key import correspond_path_key
from utils.common.data.exclimbwuzhi import ex_data
from utils.common.regex import Regex
from utils.common.enums import StatusCode

class Utils:
    referer_url = "https://www.bilibili.com/"

    @staticmethod
    def hmac_sha256(key: str, message: str):
        key = key.encode("utf-8")
        message = message.encode("utf-8")

        hmac_obj = hmac.new(key, message, hashlib.sha256)

        return hmac_obj.digest().hex()

    @classmethod
    def get_bili_ticket(cls):
        url = "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"

        params = {
            "key_id": "ec02",
            "hexsign": Utils.hmac_sha256("XgwSnGZ1p", f"ts{DateTime.get_timestamp()}"),
            "context[ts]": f"{DateTime.get_timestamp()}",
            "csrf": Config.User.bili_jct
        }

        data = cls.request_post(url, params)

        Config.Auth.bili_ticket = data["data"]["ticket"]
        Config.Auth.bili_ticket_expires = DateTime.get_timedelta(DateTime.now(), 3)

    @classmethod
    def get_nav_info(cls):
        url = "https://api.bilibili.com/x/web-interface/nav"

        data = cls.request_get(url)

        img_url: str = data["data"]["wbi_img"]["img_url"]
        sub_url: str = data["data"]["wbi_img"]["sub_url"]

        Config.User.login = data["data"]["isLogin"]

        if not Config.User.login:
            Login.clear_login_info()

        Config.Auth.img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        Config.Auth.sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]

    @classmethod
    def get_buvid3_buvid4(cls):
        url = "https://api.bilibili.com/x/frontend/finger/spi"

        data = cls.request_get(url)

        req = RequestUtils.request_get(url)
        data = json.loads(req.text)

        Config.Auth.buvid3 = data["data"]["b_3"]
        Config.Auth.buvid4 = data["data"]["b_4"]
        Config.Auth.b_nut = DateTime.get_timestamp()

    @staticmethod
    def get_uuid():
        t = DateTime.get_timestamp() % 100000
        mp = list("123456789ABCDEF") + ["10"]
        pck = [8, 4, 4, 4, 12]

        gen_part = lambda x: "".join([random.choice(mp) for _ in range(x)])  # noqa: E731

        Config.Auth.uuid = "-".join([gen_part(l) for l in pck]) + str(t).ljust(5, "0") + "infoc"  # noqa: E741

    @staticmethod
    def get_b_lsid():
        ret = ""

        for _ in range(8):
            ret += hex(random.randint(0, 15))[2:].upper()

        ret = f"{ret}_{hex(DateTime.get_timestamp())[2:].upper()}"

        Config.Auth.b_lsid = ret

    @staticmethod
    def get_buvid_fp():
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

        source = io.BytesIO(bytes(Config.Advanced.user_agent, "ascii"))
        m = murmur3_x64_128(source, 31)

        Config.Auth.buvid_fp = "{}{}".format(hex(m & (MOD - 1))[2:], hex(m >> 64)[2:])

    @classmethod
    def exclimbwuzhi(cls, template: dict, correspond_path = None):
        context = {
            "timestamp": round(time.time() * 1000),
            "uuid": Config.Auth.uuid,
            "buvid3": Config.Auth.buvid3,
            "correspond_path": correspond_path
        }

        url = "https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi"

        payload = {
            "payload": json.dumps(cls.format_dict(template, context), ensure_ascii = False)
        }
        
        cls.request_post(url, payload = payload)

    @classmethod
    def check_cookie_info(cls):
        params = {
            "csrf": Config.User.bili_jct
        }

        url = f"https://passport.bilibili.com/x/passport-login/web/cookie/info?{cls.url_encode(params)}"

        data = Utils.request_get(url)

        return data["data"]["refresh"]

    @classmethod
    def request_get(cls, url: str, html: bool = False):
        req = RequestUtils.request_get(url, RequestUtils.get_headers(referer_url = cls.referer_url, sessdata = Config.User.SESSDATA))

        req.raise_for_status()

        return req.text if html else json.loads(req.text)

    @classmethod
    def request_post(cls, url: str, params: dict = None, payload: dict = None):
        req = RequestUtils.request_post(url, params = params, json = payload, headers = RequestUtils.get_headers(referer_url = cls.referer_url, sessdata = Config.User.SESSDATA))

        req.raise_for_status()

        return json.loads(req.text)

    @staticmethod
    def check_timestamp_expires(timestamp: int):
        time_diff = DateTime.now() - DateTime.from_timestamp(timestamp)

        return time_diff.total_seconds() > 0
    
    @staticmethod
    def get_correspond_path():
        ts = round((time.time() - 30) * 1000)

        cipher = PKCS1_OAEP.new(RSA.import_key(correspond_path_key), SHA256)
        encrypted = cipher.encrypt(f"refresh_{ts}".encode())

        return binascii.b2a_hex(encrypted).decode()

    @classmethod
    def get_refresh_csrf(cls, correspond_path: str):
        url = f"https://www.bilibili.com/correspond/1/{correspond_path}"

        page = cls.request_get(url, html = True)

        match = Regex.search(r'id="1-name">(.*)</div', page)

        return match[1]

    @classmethod
    def refresh_cookie(cls, refresh_csrf: str):
        params = {
            "csrf": Config.User.bili_jct,
            "refresh_csrf": refresh_csrf,
            "source": "main_web",
            "refresh_token": Config.Auth.refresh_token
        }

        url = "https://passport.bilibili.com/x/passport-login/web/cookie/refresh"

        data = cls.request_post(url, params = params)

        if data["code"] != StatusCode.Success:
            print("refresh cookie failed:", data)
            #Login.logout()

            return False
        else:
            Config.Auth.refresh_token = data["data"]["refresh_token"]

            return True

    @classmethod
    def confirm_refresh_cookie(cls):
        params = {
            "csrf": Config.User.bili_jct,
            "refresh_token": Config.Auth.refresh_token
        }

        url = "https://passport.bilibili.com/x/passport-login/web/confirm/refresh"

        data = cls.request_post(url, params = params)

    @staticmethod
    def url_encode(params: dict):
        return urllib.parse.urlencode(params)

    @staticmethod
    def format_dict(template: dict, context: dict):
        return {
            key: value.format(**context) if isinstance(value, str) and key != "54ef" else value
            for key, value in template.items()
        }

class Cookie:
    @classmethod
    def init_cookie_params(cls):
        cookie_params = [Config.Auth.buvid3, Config.Auth.buvid4, Config.Auth.buvid_fp, Config.Auth.b_nut, Config.Auth.bili_ticket, Config.Auth.bili_ticket_expires, Config.Auth.uuid]

        if cls.params_invalid(cookie_params):
            cls.generate_cookie_params()
            
        cls.check_expires()

        Utils.get_b_lsid()
        Utils.get_nav_info()

        Utils.exclimbwuzhi(ex_data[1])

        #cls.refresh_cookie()

    @classmethod
    def check_expires(cls):
        if Utils.check_timestamp_expires(Config.Auth.bili_ticket_expires):
            Utils.get_bili_ticket()

            Config.save_user_config()
    
    @classmethod
    def generate_cookie_params(cls):
        Utils.get_uuid()
        Utils.get_buvid_fp()

        Utils.get_buvid3_buvid4()
        Utils.get_bili_ticket()

        Utils.exclimbwuzhi(ex_data[1])

        Config.save_user_config()

    @staticmethod
    def params_invalid(params: list):
        return any([not bool(i) for i in params])

    @staticmethod
    def refresh_cookie():
        if Config.User.login:
            if Utils.check_cookie_info():
                correspond_path = Utils.get_correspond_path()

                refresh_csrf = Utils.get_refresh_csrf(correspond_path = correspond_path)

                if Utils.refresh_cookie(refresh_csrf):
                    Utils.confirm_refresh_cookie()