import json

from utils.config import Config

from utils.common.request import RequestUtils

class Update:
    @classmethod
    def get_json(cls, url: str) -> dict:
        req = RequestUtils.request_get(url)

        return json.loads(req.text)
    
    @staticmethod
    def get_changelog():
        url = f"https://api.scott-sloan.cn/Bili23-Downloader/getChangelog?version_code={Config.APP.version_code}"

        return Update.get_json(url)
    
    @staticmethod
    def get_update_json():
        url = f"https://api.scott-sloan.cn/Bili23-Downloader/getLatestVersion?ver={Config.APP.version_code}"

        return Update.get_json(url)