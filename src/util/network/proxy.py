from util.common.enum import ProxyType
from util.common import config

class Proxy:
    def __init__(self):
        self.enabled = config.get(config.proxy_enabled)
        self.type = config.get(config.proxy_type)

        self.server = config.get(config.proxy_server)
        self.port = config.get(config.proxy_port)
        self.uname = config.get(config.proxy_uname)
        self.password = config.get(config.proxy_password)

    def set_data(self, data: dict):
        self.enabled = True

        self.type = data.get("type")
        self.server = data.get("server")
        self.port = data.get("port")
        self.uname = data.get("uname")
        self.password = data.get("password")

    def get_proxies(self):
        def format(protocol: str):
            if self.uname and self.password:
                return f"{protocol}://{self.uname}:{self.password}@{self.server}:{self.port}"
            else:
                return f"{protocol}://{self.server}:{self.port}"
            
        if not self.enabled:
            return None
            
        match self.type:
            case ProxyType.HTTP:
                return {
                    "http": format("http"),
                    "https": format("http")
                }
            
            case ProxyType.SOCKS4:
                return {
                    "http": format("socks4"),
                    "https": format("socks4")
                }
            
            case ProxyType.SOCKS5:
                return {
                    "http": format("socks5"),
                    "https": format("socks5")
                }
