import json

from utils.common.request import RequestUtils

class LoginInfo:
    url: str = ""
    qrcode_key: str = ""

class Login:
    class QRCode:
        def generate_qrcode(self):
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

            req = RequestUtils.request_get(url)
            resp = json.loads(req.text)

            LoginInfo.url = resp["data"]["url"]
            LoginInfo.qrcode_key = resp["data"]["qrcode_key"]

    class SMS:
        pass