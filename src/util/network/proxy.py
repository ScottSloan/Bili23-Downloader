from ..common.enum import ProxyMode, ProxyType
from ..common.config import config

class Proxy:
    def __init__(self):
        self.mode = config.get(config.proxy_mode)
        self.type = config.get(config.proxy_type)

        self.server = config.get(config.proxy_server)
        self.port = config.get(config.proxy_port)
        self.uname = config.get(config.proxy_uname)
        self.password = config.get(config.proxy_password)

    def set_data(self, data: dict):
        # 供代理测试使用：无论当前是哪种模式，都以传入的这份配置为准
        self.mode = ProxyMode.MANUAL

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
            
        # 仅手动设置模式才使用程序内配置的代理服务器，其余模式交由调用方处理
        if self.mode != ProxyMode.MANUAL:
            return None
            
        match self.type:
            case ProxyType.HTTP:
                return {
                    "http": format("http"),
                    "https": format("http")
                }
            
            # case ProxyType.SOCKS4:
            #     return {
            #         "http": format("socks4"),
            #         "https": format("socks4")
            #     }
            
            # case ProxyType.SOCKS5:
            #     return {
            #         "http": format("socks5"),
            #         "https": format("socks5")
            #     }
