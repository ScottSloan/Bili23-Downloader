import json
import time
import qrcode
import requests
from io import BytesIO

from utils.tools import get_exclimbwuzhi_header, get_login_header
from utils.tool_v2 import RequestTool
from utils.config import Config, ConfigUtils
from utils.common.enums import StatusCode

class LoginInfo:
    url: str = ""
    qrcode_key: str = ""

    token: str = ""
    challenge: str = ""
    gt: str = ""

    validate: str = ""
    seccode: str = ""

    captcha_key: str = ""

class LoginBase:
    # 登录基类
    def __init__(self, session: requests.sessions.Session):
        self.session = session

    def get_user_info(self, refresh = False):
        url = "https://api.bilibili.com/x/web-interface/nav"

        # 判断是否刷新用户信息
        if refresh:
            headers = RequestTool.get_headers(sessdata = Config.User.sessdata)

        else:
            headers = RequestTool.get_headers()
            
            headers["Cookie"] = ";".join([f'{key}={value}' for (key, value) in self.session.cookies.items()])

        req = self.session.get(url, headers = headers, proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        resp = json.loads(req.text)["data"]
                
        return {
            "username": resp["uname"],
            "face_url": resp["face"],
            "sessdata": self.session.cookies["SESSDATA"] if not refresh else Config.User.sessdata,
            "login_time": round(time.time())
        }

    def logout(self):
        Config.User.login = False
        Config.User.face_url = Config.User.username = Config.User.sessdata = ""

        kwargs = {
            "login": False,
            "face_url": "",
            "username": "",
            "sessdata": "",
            "timestamp": 0
        }

        utils = ConfigUtils()
        utils.update_config_kwargs(Config.User.user_config_path, "user", **kwargs)
    
class QRLogin(LoginBase):
    def __init__(self, session):
        LoginBase.__init__(self, session)

    def init_qrcode(self):
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

        req = self.session.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        LoginInfo.url = resp["data"]["url"]
        LoginInfo.qrcode_key = resp["data"]["qrcode_key"]
    
    def get_qrcode(self):
        pic = BytesIO()

        qrcode.make(LoginInfo.url).save(pic)

        return pic.getvalue()
    
    def check_scan(self):
        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={LoginInfo.qrcode_key}"

        req = self.session.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        req_json = json.loads(req.text)

        return {
            "message": req_json["data"]["message"],
            "code": req_json["data"]["code"]}

class SMSLogin(LoginBase):
    def __init__(self, session):
        LoginBase.__init__(self, session)

    def get_country_list(self):
        url = "https://passport.bilibili.com/x/passport-login/web/country"

        req = self.session.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        data = json.loads(req.text)

        return data

    def send_sms(self, tel: int, cid: int):
        url = "https://passport.bilibili.com/x/passport-login/web/sms/send"

        form = {
            "cid": cid,
            "tel": tel,
            "source": "main-fe-header",
            "token": LoginInfo.token,
            "challenge": LoginInfo.challenge,
            "validate": LoginInfo.validate,
            "seccode": LoginInfo.seccode
        }

        req = self.session.post(url, params = form, headers = get_login_header(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        data = json.loads(req.text)

        if data["code"]  == StatusCode.Success.value:
            # 只有短信发送成功时才设置 captcha_key
            LoginInfo.captcha_key = data["data"]["captcha_key"]

        return data

    def login(self, tel: int, code: int, cid: int):
        url = "https://passport.bilibili.com/x/passport-login/web/login/sms"

        form = {
            "cid": cid,
            "tel": tel,
            "code": code,
            "source": "main-fe-header",
            "captcha_key": LoginInfo.captcha_key
        }
        
        req = self.session.post(url, params = form, headers = get_login_header(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        data = json.loads(req.text)

        return data

    def ExClimbWuzhi(self):
        # 激活浏览器指纹
        url = "https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi"
        
        payload = {"payload": '{\"3064\":1,\"5062\":\"' + str(int(time.time() * 1000)) + '\",\"03bf\":\"https://www.bilibili.com/\",\"39c8\":\"333.42.fp.risk\",\"34f1\":\"\",\"d402\":\"\",\"654a\":\"\",\"6e7c\":\"1699x800\",\"3c43\":{\"2673\":0,\"5766\":24,\"6527\":0,\"7003\":1,\"807e\":1,\"b8ce\":\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0\",\"641c\":0,\"07a4\":\"zh-CN\",\"1c57\":8,\"0bd0\":20,\"748e\":[960,1707],\"d61f\":[912,1707],\"fc9d\":-480,\"6aa9\":\"Asia/Shanghai\",\"75b8\":1,\"3b21\":1,\"8a1c\":0,\"d52f\":\"not available\",\"adca\":\"Win32\",\"80c9\":[[\"PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Chrome PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Chromium PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"Microsoft Edge PDF Viewer\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]],[\"WebKit built-in PDF\",\"Portable Document Format\",[[\"application/pdf\",\"pdf\"],[\"text/pdf\",\"pdf\"]]]],\"13ab\":\"tgAAAABJRU5ErkJggg==\",\"bfe9\":\"tIBiiQjAIAKxmrSRQF9Cvwf5Sw9aZdePLEAAAAAElFTkSuQmCC\",\"a3c1\":[\"extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_clip_control;EXT_color_buffer_half_float;EXT_depth_clamp;EXT_disjoint_timer_query;EXT_float_blend;EXT_frag_depth;EXT_polygon_offset_clamp;EXT_shader_texture_lod;EXT_texture_compression_bptc;EXT_texture_compression_rgtc;EXT_texture_filter_anisotropic;EXT_texture_mirror_clamp_to_edge;EXT_sRGB;KHR_parallel_shader_compile;OES_element_index_uint;OES_fbo_render_mipmap;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_blend_func_extended;WEBGL_color_buffer_float;WEBGL_compressed_texture_s3tc;WEBGL_compressed_texture_s3tc_srgb;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBGL_multi_draw;WEBGL_polygon_mode\",\"webgl aliased line width range:[1, 1]\",\"webgl aliased point size range:[1, 1024]\",\"webgl alpha bits:8\",\"webgl antialiasing:yes\",\"webgl blue bits:8\",\"webgl depth bits:24\",\"webgl green bits:8\",\"webgl max anisotropy:16\",\"webgl max combined texture image units:32\",\"webgl max cube map texture size:16384\",\"webgl max fragment uniform vectors:1024\",\"webgl max render buffer size:16384\",\"webgl max texture image units:16\",\"webgl max texture size:16384\",\"webgl max varying vectors:30\",\"webgl max vertex attribs:16\",\"webgl max vertex texture image units:16\",\"webgl max vertex uniform vectors:4095\",\"webgl max viewport dims:[32767, 32767]\",\"webgl red bits:8\",\"webgl renderer:WebKit WebGL\",\"webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)\",\"webgl stencil bits:0\",\"webgl vendor:WebKit\",\"webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)\",\"webgl unmasked vendor:Google Inc. (NVIDIA)\",\"webgl unmasked renderer:ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Laptop GPU (0x000028E0) Direct3D11 vs_5_0 ps_5_0, D3D11)\",\"webgl vertex shader high float precision:23\",\"webgl vertex shader high float precision rangeMin:127\",\"webgl vertex shader high float precision rangeMax:127\",\"webgl vertex shader medium float precision:23\",\"webgl vertex shader medium float precision rangeMin:127\",\"webgl vertex shader medium float precision rangeMax:127\",\"webgl vertex shader low float precision:23\",\"webgl vertex shader low float precision rangeMin:127\",\"webgl vertex shader low float precision rangeMax:127\",\"webgl fragment shader high float precision:23\",\"webgl fragment shader high float precision rangeMin:127\",\"webgl fragment shader high float precision rangeMax:127\",\"webgl fragment shader medium float precision:23\",\"webgl fragment shader medium float precision rangeMin:127\",\"webgl fragment shader medium float precision rangeMax:127\",\"webgl fragment shader low float precision:23\",\"webgl fragment shader low float precision rangeMin:127\",\"webgl fragment shader low float precision rangeMax:127\",\"webgl vertex shader high int precision:0\",\"webgl vertex shader high int precision rangeMin:31\",\"webgl vertex shader high int precision rangeMax:30\",\"webgl vertex shader medium int precision:0\",\"webgl vertex shader medium int precision rangeMin:31\",\"webgl vertex shader medium int precision rangeMax:30\",\"webgl vertex shader low int precision:0\",\"webgl vertex shader low int precision rangeMin:31\",\"webgl vertex shader low int precision rangeMax:30\",\"webgl fragment shader high int precision:0\",\"webgl fragment shader high int precision rangeMin:31\",\"webgl fragment shader high int precision rangeMax:30\",\"webgl fragment shader medium int precision:0\",\"webgl fragment shader medium int precision rangeMin:31\",\"webgl fragment shader medium int precision rangeMax:30\",\"webgl fragment shader low int precision:0\",\"webgl fragment shader low int precision rangeMin:31\",\"webgl fragment shader low int precision rangeMax:30\"],\"6bc5\":\"Google Inc. (NVIDIA)~ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Laptop GPU (0x000028E0) Direct3D11 vs_5_0 ps_5_0, D3D11)\",\"ed31\":0,\"72bd\":0,\"097b\":0,\"52cd\":[0,0,0],\"a658\":[\"Arial\",\"Arial Black\",\"Arial Narrow\",\"Book Antiqua\",\"Bookman Old Style\",\"Calibri\",\"Cambria\",\"Cambria Math\",\"Century\",\"Century Gothic\",\"Century Schoolbook\",\"Comic Sans MS\",\"Consolas\",\"Courier\",\"Courier New\",\"Georgia\",\"Helvetica\",\"Impact\",\"Lucida Bright\",\"Lucida Calligraphy\",\"Lucida Console\",\"Lucida Fax\",\"Lucida Handwriting\",\"Lucida Sans\",\"Lucida Sans Typewriter\",\"Lucida Sans Unicode\",\"Microsoft Sans Serif\",\"Monotype Corsiva\",\"MS Gothic\",\"MS PGothic\",\"MS Reference Sans Serif\",\"MS Sans Serif\",\"MS Serif\",\"Palatino Linotype\",\"Segoe Print\",\"Segoe Script\",\"Segoe UI\",\"Segoe UI Light\",\"Segoe UI Semibold\",\"Segoe UI Symbol\",\"Tahoma\",\"Times\",\"Times New Roman\",\"Trebuchet MS\",\"Verdana\",\"Wingdings\",\"Wingdings 2\",\"Wingdings 3\"],\"d02f\":\"124.04347527516074\"},\"54ef\":\"{\\"b_ut\\":null,\\"home_version\\":\\"V8\\",\\"i-wanna-go-back\\":null,\\"in_new_ab\\":true,\\"ab_version\\":{\\"for_ai_home_version\\":\\"V8\\",\\"tianma_banner_inline\\":\\"CONTROL\\",\\"enable_web_push\\":\\"DISABLE\\",\\"enable_player_bar\\":\\"DISABLE\\"},\\"ab_split_num\\":{\\"for_ai_home_version\\":54,\\"tianma_banner_inline\\":54,\\"enable_web_push\\":10,\\"enable_player_bar\\":54}}\",\"8b94\":\"\",\"df35\":\"' + Config.Auth.buvid3 + '\",\"07a4\":\"zh-CN\",\"5f45\":null,\"db46\":0}'}

        self.session.post(url, json = payload, headers = get_exclimbwuzhi_header(), proxies = RequestTool.get_headers(), auth = RequestTool.get_auth())

class CaptchaUtils:
    def __init__(self):
        pass

    def get_geetest_challenge_gt(self):
        req = requests.get("https://passport.bilibili.com/x/passport-login/captcha?source=main-fe-header&t=0.1867987009754133", headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        data = json.loads(req.text)

        LoginInfo.token = data["data"]["token"]
        LoginInfo.challenge = data["data"]["geetest"]["challenge"]
        LoginInfo.gt = data["data"]["geetest"]["gt"]
