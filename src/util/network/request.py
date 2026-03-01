from PySide6.QtCore import Signal, QObject, Slot

from util.common.config import config
from util.network.proxy import Proxy

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from enum import Enum

import requests

session = requests.Session()

retry_strategy = Retry(
    total = 3,
    backoff_factor = 1,
    status_forcelist = [429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(
    pool_connections = 5,
    pool_maxsize = 10,
    max_retries = retry_strategy
)

session.mount("http://", adapter)
session.mount("https://", adapter)

session.headers.update({
    "Referer": "https://www.bilibili.com/",
    "User-Agent": config.get(config.user_agent)
})

class RequestType(Enum):
    GET = 0
    POST = 1
    HEAD = 2

class ResponseType(Enum):
    TEXT = 0
    JSON = 1
    BYTES = 2
    HEADERS = 3
    REDIRECT_URL = 4

class NetworkRequestWorker(QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True):
        super().__init__()

        self.url = url
        self.params = params
        self.request_type = request_type
        self.response_type = response_type
        self.raise_for_status = raise_for_status

        self.proxies = Proxy().get_proxies()

    @Slot()
    def run(self):
        try:
            match self.request_type:
                case RequestType.GET:
                    func = session.get
                
                case RequestType.POST:
                    func = session.post
                
                case RequestType.HEAD:
                    func = session.head

            res = func(url = self.url, proxies = self.proxies, params = self.params, allow_redirects = True, timeout = 5)

            if self.raise_for_status:
                res.raise_for_status()

            match self.response_type:
                case ResponseType.TEXT:
                    resp = res.text

                case ResponseType.JSON:
                    resp = res.json()

                case ResponseType.BYTES:
                    resp = res.content

                case ResponseType.HEADERS:
                    resp = res.headers

                case ResponseType.REDIRECT_URL:
                    resp = res.url

            self.success.emit(resp)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.proxies = None

            self.finished.emit()

    def set_proxies(self, proxies: dict):
        self.proxies = proxies

def get_cookies():
    cookies = {
        "_uuid": config.get(config.uuid),
        "b_lsid": config.get(config.b_lsid),
        "b_nut": str(config.get(config.b_nut)),
        "bili_ticket": config.get(config.bili_ticket),
        "bili_ticket_expires": str(config.get(config.bili_ticket_expires)),
        "buvid_fp": config.get(config.buvid_fp),
        "buvid3": config.get(config.buvid3),
        "buvid4": config.get(config.buvid4),
        "CURRENT_FNVAL": "4048",
        "CURRENT_QUALITY": "0"
    }

    if config.get(config.is_login):
        cookies["bili_jct"] = config.get(config.bili_jct)
        cookies["DedeUserID"] = config.get(config.DedeUserID)
        cookies["DedeUserID__ckMd5"] = config.get(config.DedeUserID__ckMd5)
        cookies["SESSDATA"] = config.get(config.SESSDATA)

    return cookies

def update_cookies():
    cookies = get_cookies()

    for key, value in cookies.items():
        session.cookies.set(
            name = key,
            value = value,
            domain = ".bilibili.com",
            path = "/"
        )

update_cookies()
