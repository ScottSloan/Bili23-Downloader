import io
import json
import hmac
import time
import random
import struct
import hashlib
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, wait

from utils.tool_v2 import RequestTool
from utils.config import Config, ConfigMgr

class CookieUtils:
    def __init__(self):
        pass

    def checkCookieInfo(self):
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        return resp["data"]["refresh"]
    
    def init_cookie_params(self):
        cookie_params = [Config.Auth.buvid3, Config.Auth.buvid4, Config.Auth.buvid_fp, Config.Auth.b_nut, Config.Auth.bili_ticket, Config.Auth.bili_ticket_expires, Config.Auth.uuid]
        user_params = [Config.User.SESSDATA, Config.User.bili_jct, Config.User.DedeUserID, Config.User.DedeUserID__ckMd5, Config.User.login_expires]

        if self.params_invalid(cookie_params):
            self.generate_cookie_params()

        if self.params_invalid(user_params) and Config.User.login:
            self.reset_user_params()

        self.check_bili_ticket_expires()
        self.check_login_expires()

        self.gen_b_lsid()
        self.get_wbi_keys()

    def check_bili_ticket_expires(self):
        if self.check_timestamp_expires(Config.Auth.bili_ticket_expires):
            self.get_bili_ticket()

            kwargs = {
                "bili_ticket": Config.Auth.bili_ticket,
                "bili_ticket_expires": Config.Auth.bili_ticket_expires
            }

            self.update_cookie_params(kwargs)

    def check_login_expires(self):
        if self.check_timestamp_expires(Config.User.login_expires) and Config.User.login:
            self.reset_user_params()
    
    def generate_cookie_params(self):
        self.gen_uuid()
        self.gen_buvid_fp()

        task = []

        thread_pool = ThreadPoolExecutor(max_workers = 2)
        task.append(thread_pool.submit(self.get_buvid3_buvid4))
        task.append(thread_pool.submit(self.get_bili_ticket))

        wait(task)

        self.exclimbwuzhi(Config.Auth.uuid)

        kwargs = {
            "buvid3": Config.Auth.buvid3,
            "buvid4": Config.Auth.buvid4,
            "buvid_fp": "20dcd229181e846ea1c7b4fb797068b1",
            "b_nut": Config.Auth.b_nut,
            "bili_ticket": Config.Auth.bili_ticket,
            "bili_ticket_expires": Config.Auth.bili_ticket_expires,
            "uuid": Config.Auth.uuid,
        }

        self.update_cookie_params(kwargs)

    def update_cookie_params(self, kwargs: dict, category: str = "cookie_params"):
        ConfigMgr.update_config_kwargs(Config.User.user_config_path, category, **kwargs)

    def reset_user_params(self):
        Config.User.login = False
        Config.User.username = Config.User.face_url = Config.User.SESSDATA = Config.User.bili_jct = Config.User.DedeUserID = Config.User.DedeUserID__ckMd5 = ""
        Config.User.login_expires = 0

        Config.Temp.need_login = True

        kwargs = {
            "login": Config.User.login,
            "username": Config.User.username,
            "face_url": Config.User.face_url,
            "SESSDATA": Config.User.SESSDATA,
            "bili_jct": Config.User.bili_jct,
            "DedeUserID": Config.User.DedeUserID,
            "DedeUserID__ckMd5": Config.User.DedeUserID__ckMd5,
            "login_expires": Config.User.login_expires
        }

        self.update_cookie_params(kwargs, category = "user")

    def params_invalid(self, params: list):
        return any([not bool(i) for i in params])

    def get_bili_ticket(self):
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

        Config.Auth.bili_ticket = data["data"]["ticket"]
        Config.Auth.bili_ticket_expires = int((datetime.now() + timedelta(days = 3)).timestamp())
    
    def get_buvid3_buvid4(self):
        url = "https://api.bilibili.com/x/frontend/finger/spi"

        req = RequestTool.request_get(url)
        data = json.loads(req.text)

        Config.Auth.buvid3 = data["data"]["b_3"]
        Config.Auth.buvid4 = data["data"]["b_4"]
        Config.Auth.b_nut = int(datetime.timestamp(datetime.now()))

    def get_wbi_keys(self):
        url = "https://api.bilibili.com/x/web-interface/nav"

        req = RequestTool.request_get(url)
        data = json.loads(req.text)

        img_url: str = data["data"]["wbi_img"]["img_url"]
        sub_url: str = data["data"]["wbi_img"]["sub_url"]

        Config.Auth.img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        Config.Auth.sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]

    def gen_uuid(self):
        t = self.get_timestamp() % 100000
        mp = list("123456789ABCDEF") + ["10"]
        pck = [8, 4, 4, 4, 12]

        gen_part = lambda x: "".join([random.choice(mp) for _ in range(x)])  # noqa: E731

        Config.Auth.uuid = "-".join([gen_part(l) for l in pck]) + str(t).ljust(5, "0") + "infoc"  # noqa: E741

    def gen_b_lsid(self):
        ret = ""

        for _ in range(8):
            ret += hex(random.randint(0, 15))[2:].upper()

        ret = f"{ret}_{hex(self.get_timestamp())[2:].upper()}"

        Config.Auth.b_lsid = ret

    def gen_buvid_fp(self):
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

        source = io.BytesIO(bytes(RequestTool.USER_AGENT, "ascii"))
        m = murmur3_x64_128(source, 31)

        Config.Auth.buvid_fp = "{}{}".format(hex(m & (MOD - 1))[2:], hex(m >> 64)[2:])

    def exclimbwuzhi(self, df35: str):
        url = "https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi"
        
        payload = {"payload": '{\"3064\":1,\"5062\":\"' + str(int(datetime.timestamp(datetime.now())))+ '\",\"03bf\":\"https://www.bilibili.com/\",\"39c8\":\"333.42.fp.risk\",\"34f1\":\"\",\"d402\":\"\",\"654a\":\"\",\"6e7c\":\"1699x800\",\"3c43\":{\"2673\":0,\"5766\":24,\"6527\":0,\"7003\":1,\"807e\":1,\"b8ce\":\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0\",\"641c\":0,\"07a4\":\"zh-CN\",\"1c57\":8,\"0bd0\":20,\"748e\":[960,1707],\"d61f\":[912,1707],\"fc9d\":-480,\"6aa9\":\"Asia/Shanghai\",\"75b8\":1,\"3b21\":1,\"8a1c\":0,\"d52f\":\"not available\",\"adca\":\"Win32\",\"80c9\":[[\"PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Chrome PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Chromium PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Microsoft Edge PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"WebKit built-in PDF\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]]],\"13ab\":\"tgAAAABJRU5ErkJggg==\",\"bfe9\":\"tIBiiQjAIAKxmrSRQF9Cvwf5Sw9aZdePLEAAAAAElFTkSuQmCC\",\"a3c1\":[\"extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_clip_control;EXT_color_buffer_half_float;EXT_depth_clamp;EXT_disjoint_timer_query;EXT_float_blend;EXT_frag_depth;EXT_polygon_offset_clamp;EXT_shader_texture_lod;EXT_texture_compression_bptc;EXT_texture_compression_rgtc;EXT_texture_filter_anisotropic;EXT_texture_mirror_clamp_to_edge;EXT_sRGB;KHR_parallel_shader_compile;OES_element_index_uint;OES_fbo_render_mipmap;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_blend_func_extended;WEBGL_color_buffer_float;WEBGL_compressed_texture_s3tc;WEBGL_compressed_texture_s3tc_srgb;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBGL_multi_draw;WEBGL_polygon_mode\",\"webgl aliased line width range:[1, 1]\",\"webgl aliased point size range:[1, 1024]\",\"webgl alpha bits:8\",\"webgl antialiasing:yes\",\"webgl blue bits:8\",\"webgl depth bits:24\",\"webgl green bits:8\",\"webgl max anisotropy:16\",\"webgl max combined texture image units:32\",\"webgl max cube map texture size:16384\",\"webgl max fragment uniform vectors:1024\",\"webgl max render buffer size:16384\",\"webgl max texture image units:16\",\"webgl max texture size:16384\",\"webgl max varying vectors:30\",\"webgl max vertex attribs:16\",\"webgl max vertex texture image units:16\",\"webgl max vertex uniform vectors:4095\",\"webgl max viewport dims:[32767, 32767]\",\"webgl red bits:8\",\"webgl renderer:WebKit WebGL\",\"webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)\",\"webgl stencil bits:0\",\"webgl vendor:WebKit\",\"webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)\",\"webgl unmasked vendor:Google Inc. (NVIDIA)\",\"webgl unmasked renderer:ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Laptop GPU (0x000028E0) Direct3D11 vs_5_0 ps_5_0, D3D11)\",\"webgl vertex shader high float precision:23\",\"webgl vertex shader high float precision rangeMin:127\",\"webgl vertex shader high float precision rangeMax:127\",\"webgl vertex shader medium float precision:23\",\"webgl vertex shader medium float precision rangeMin:127\",\"webgl vertex shader medium float precision rangeMax:127\",\"webgl vertex shader low float precision:23\",\"webgl vertex shader low float precision rangeMin:127\",\"webgl vertex shader low float precision rangeMax:127\",\"webgl fragment shader high float precision:23\",\"webgl fragment shader high float precision rangeMin:127\",\"webgl fragment shader high float precision rangeMax:127\",\"webgl fragment shader medium float precision:23\",\"webgl fragment shader medium float precision rangeMin:127\",\"webgl fragment shader medium float precision rangeMax:127\",\"webgl fragment shader low float precision:23\",\"webgl fragment shader low float precision rangeMin:127\",\"webgl fragment shader low float precision rangeMax:127\",\"webgl vertex shader high int precision:0\",\"webgl vertex shader high int precision rangeMin:31\",\"webgl vertex shader high int precision rangeMax:30\",\"webgl vertex shader medium int precision:0\",\"webgl vertex shader medium int precision rangeMin:31\",\"webgl vertex shader medium int precision rangeMax:30\",\"webgl vertex shader low int precision:0\",\"webgl vertex shader low int precision rangeMin:31\",\"webgl vertex shader low int precision rangeMax:30\",\"webgl fragment shader high int precision:0\",\"webgl fragment shader high int precision rangeMin:31\",\"webgl fragment shader high int precision rangeMax:30\",\"webgl fragment shader medium int precision:0\",\"webgl fragment shader medium int precision rangeMin:31\",\"webgl fragment shader medium int precision rangeMax:30\",\"webgl fragment shader low int precision:0\",\"webgl fragment shader low int precision rangeMin:31\",\"webgl fragment shader low int precision rangeMax:30\"],\"6bc5\":\"Google Inc. (NVIDIA)~ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Laptop GPU (0x000028E0) Direct3D11 vs_5_0 ps_5_0, D3D11)\",\"ed31\":0,\"72bd\":0,\"097b\":0,\"52cd\":[0,0,0],\"a658\":[\"Arial\",\"Arial Black\",\"Arial Narrow\",\"Book Antiqua\",\"Bookman Old Style\",\"Calibri\",\"Cambria\",\"Cambria Math\",\"Century\",\"Century Gothic\",\"Century Schoolbook\",\"Comic Sans MS\",\"Consolas\",\"Courier\",\"Courier New\",\"Georgia\",\"Helvetica\",\"Impact\",\"Lucida Bright\",\"Lucida Calligraphy\",\"Lucida Console\",\"Lucida Fax\",\"Lucida Handwriting\",\"Lucida Sans\",\"Lucida Sans Typewriter\",\"Lucida Sans Unicode\",\"Microsoft Sans Serif\",\"Monotype Corsiva\",\"MS Gothic\",\"MS PGothic\",\"MS Reference Sans Serif\",\"MS Sans Serif\",\"MS Serif\",\"Palatino Linotype\",\"Segoe Print\",\"Segoe Script\",\"Segoe UI\",\"Segoe UI Light\",\"Segoe UI Semibold\",\"Segoe UI Symbol\",\"Tahoma\",\"Times\",\"Times New Roman\",\"Trebuchet MS\",\"Verdana\",\"Wingdings\",\"Wingdings 2\",\"Wingdings 3\"],\"d02f\":\"124.04347527516074\"},\"54ef\":\"{\\"b_ut\\":null,\\"home_version\\":\\"V8\\",\\"i-wanna-go-back\\":null,\\"in_new_ab\\":true,\\"ab_version\\":{\\"for_ai_home_version\\":\\"V8\\",\\"tianma_banner_inline\\":\\"CONTROL\\",\\"enable_web_push\\":\\"DISABLE\\",\\"enable_player_bar\\":\\"DISABLE\\"},\\"ab_split_num\\":{\\"for_ai_home_version\\":54,\\"tianma_banner_inline\\":54,\\"enable_web_push\\":10,\\"enable_player_bar\\":54}}\",\"8b94\":\"\",\"df35\":\"' + df35 + '\",\"07a4\":\"zh-CN\",\"5f45\":null,\"db46\":0}'}

        RequestTool.request_post(url, json = payload)

    def check_timestamp_expires(self, timestamp: int):
        time_diff = datetime.now() - datetime.fromtimestamp(timestamp)

        return time_diff.total_seconds() > 0

    def get_timestamp(self):
        return int(datetime.timestamp(datetime.now()))