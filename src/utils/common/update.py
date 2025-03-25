import json

from utils.tool_v2 import RequestTool
from utils.config import Config

class Update:
    def get_json(url: str):
        return json.loads(RequestTool.request_get(url).text)
    
    def get_changelog():
        try:
            url = f"https://api.scott-sloan.cn/Bili23-Downloader/getChangelog?version_code={Config.APP.version_code}"

            Config.Temp.changelog = Update.get_json(url)

        except Exception:
            pass

    def get_update():
        try:
            url = "https://api.scott-sloan.cn/Bili23-Downloader/getLatestVersion"

            Config.Temp.update_json = Update.get_json(url)

        except Exception:
            pass