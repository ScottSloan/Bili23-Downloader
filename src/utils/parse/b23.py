from utils.common.data_type import ParseCallback
from utils.common.exception import GlobalException
from utils.common.enums import StatusCode
from utils.tool_v2 import RequestTool

class B23Parser:
    def __init__(self, callback: ParseCallback):
        self.callback = callback

    def get_redirect_url(self, url: str):
        req = RequestTool.request_get(url, headers = RequestTool.get_headers())
    
        return req.url

    def parse_url(self, url: str):
        def worker():
            new_url = self.get_redirect_url(url)

            raise GlobalException(code = StatusCode.Redirect.value, callback = self.callback.redirect_callback, url = new_url)

        try:
            return worker()
        
        except Exception as e:
            raise GlobalException(callback = self.callback.error_callback) from e