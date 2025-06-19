import json

from utils.config import Config

from utils.common.request import RequestUtils

class Update:
    @staticmethod
    def get_json(url: str):
        return json.loads(RequestUtils.request_get(url).text)
    
    @staticmethod
    def get_changelog():
        try:
            url = f"https://api.scott-sloan.cn/Bili23-Downloader/getChangelog?version_code={Config.APP.version_code}"

            Config.Temp.changelog = Update.get_json(url)

        except Exception:
            pass
    
    @staticmethod
    def get_update_json():
        try:
            url = "https://api.scott-sloan.cn/Bili23-Downloader/getLatestVersion"

            Config.Temp.update_json = Update.get_json(url)

        except Exception:
            pass