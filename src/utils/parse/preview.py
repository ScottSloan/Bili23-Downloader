from utils.common.enums import ParseType
from utils.tool_v2 import RequestTool

from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.cheese import CheeseInfo

from utils.module.cdn import CDN

class Preview:
    def __init__(self, parse_type: ParseType):
        self.parse_type = parse_type

    def get_download_json(self):
        match self.parse_type:
            case ParseType.Video:
                return VideoInfo.download_json

            case ParseType.Bangumi:
                return BangumiInfo.download_json

            case ParseType.Cheese:
                return CheeseInfo.download_json

    def get_video_stream_size(self, video_quality_id: int, video_codec_id: int):
        def get_url_list():
            download_json = self.get_download_json()

            for entry in download_json["dash"]["video"]:
                if entry["id"] == video_quality_id and entry["codecid"] == video_codec_id:
                    return self.get_stream_download_url_list(entry)

        def request_head(url: str, cdn: str):
            return RequestTool.request_head(CDN.replace_cdn(url, cdn), headers = RequestTool.get_headers("https://www.bilibili.com"))

        cdn_list = CDN.get_cdn_list()

        for url in get_url_list():
            for cdn in cdn_list:
                req = request_head(url, cdn)

                if "Content-Length" in req.headers:
                    file_size = int(req.headers.get("Content-Length"))

                    if file_size:
                        return file_size

    def get_stream_download_url_list(self, data: dict):
        def generator(x: list):
            for v in x:
                if isinstance(v, list):
                    for y in v:
                        yield y
                else:
                    yield v

        return [i for i in generator([data[n] for n in ["backupUrl", "backup_url", "baseUrl", "base_url", "url"] if n in data])]