from util.network import SyncNetWorkRequest, ResponseType
from util.common import Translator

class B23Parser:
    def __init__(self):
        pass
    
    def parse(self, url: str) -> str:
        self.url = self._normalize_url(url)
        
        request = SyncNetWorkRequest(self.url, response_type = ResponseType.REDIRECT_URL)
        response = request.run()

        if response == self.url:
            self.on_error(Translator.ERROR_MESSAGES("B23_TV_URL_EXPIRED"))

        return response
    
    def _normalize_url(self, url: str) -> str:
        # 去除 url 前的无效字符，确保以 https:// 开头
        if url.startswith("https://"):
            return url

        # 如果 url 协议头前存在无效字符，尝试找到第一个 https:// 的位置
        https_pos = url.find("https://")

        if https_pos == -1:
            self.on_error(Translator.ERROR_MESSAGES("INVALID_LINK"))

        return url[https_pos:]
    
    def on_error(self, error: str):
        raise Exception(error)
