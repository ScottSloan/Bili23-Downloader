from utils.common.data_type import ParseCallback
from utils.common.exception import GlobalException
from utils.common.enums import StatusCode
from utils.common.request import RequestUtils

from utils.parse.parser import Parser

class B23Parser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()
        
        self.callback = callback

    def get_redirect_url(self, url: str):
        req = RequestUtils.request_get(url, headers = RequestUtils.get_headers())
    
        return req.url

    def parse_url(self, url: str):
        def worker():
            new_url = self.get_redirect_url(url)

            raise GlobalException(code = StatusCode.Redirect.value, callback = self.callback.onBangumi, args = (new_url, ))

        try:
            return worker()
        
        except Exception as e:
            raise GlobalException(callback = self.callback.onError) from e