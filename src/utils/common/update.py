import json

from utils.config import Config

from utils.common.request import RequestUtils

class Update:
    @staticmethod
    def get_json(url: str) -> dict:
        try:
            req = RequestUtils.request_get(url)

            return json.loads(req.text)
        
        except Exception as e:
            return None
    
    @staticmethod
    def get_changelog():
        url = f"https://api.scott-sloan.cn/Bili23-Downloader/getChangelog?version_code={Config.APP.version_code}"

        return Update.get_json(url)
    
    @staticmethod
    def get_update_json():
        url = "https://api.scott-sloan.cn/Bili23-Downloader/getLatestVersion"

        return Update.get_json(url)