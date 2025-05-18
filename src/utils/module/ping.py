import re
import subprocess

from utils.config import Config
from utils.common.enums import Platform

class Ping:
    @classmethod
    def get_ping_cmd(cls, cdn: str) -> str:
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return f"ping {cdn}"
            
            case Platform.Linux | Platform.macOS:
                return f"ping {cdn} -c 4"
    
    @classmethod
    def get_latency(cls, process):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return re.findall(r"Average = ([0-9]*)", process.stdout)
            
            case Platform.Linux | Platform.macOS:
                _temp = re.findall(r"time=([0-9]*)", process.stdout)

                if _temp:
                    return [int(sum(list(map(int, _temp))) / len(_temp))]
                else:
                    return None
    
    @classmethod
    def run(cls, cdn: str):
        process = subprocess.run(cls.get_ping_cmd(cdn), stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True, encoding = "utf-8")
        latency = cls.get_latency(process)

        if latency:
            result = f"{latency[0]}ms"
        else:
            result = "请求超时"

        return result