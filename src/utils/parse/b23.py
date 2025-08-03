from utils.common.regex import Regex

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
        b23_url = Regex.find_string(f"(http.*?)$", url)

        req = RequestUtils.request_get(b23_url, headers = RequestUtils.get_headers())
    
        return req.url

    def parse_worker(self, url: str):
        new_url = self.get_redirect_url(url)

        raise GlobalException(code = StatusCode.Redirect.value, callback = self.callback.onJump, args = (new_url, ))