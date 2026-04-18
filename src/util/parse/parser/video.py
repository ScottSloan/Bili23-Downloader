from util.network import SyncNetWorkRequest

from ..episode.video import VideoEpisodeParser
from .base import ParserBase

class VideoParser(ParserBase):
    def __init__(self):
        super().__init__()
        
    def get_aid(self):
        aid = self.find_str(r"av([0-9]+)", self.url)

        return self.aid_to_bvid(int(aid))

    def get_bvid(self):
        bvid = self.find_str(r"BV\w+", self.url)

        return bvid

    def aid_to_bvid(self, aid: int):
        XOR_CODE = 23442827791579
        MAX_AID = 1 << 51
        ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
        ENCODE_MAP = 8, 7, 0, 5, 1, 3, 2, 4, 6

        bvid = [""] * 9
        tmp = (MAX_AID | aid) ^ XOR_CODE

        for i in range(len(ENCODE_MAP)):
            bvid[ENCODE_MAP[i]] = ALPHABET[tmp % len(ALPHABET)]
            tmp //= len(ALPHABET)

        return "BV1" + "".join(bvid)

    def parse(self, url: str, pn: int):
        self.url = url

        match self.find_str(r"av|BV", url):
            case "av":
                self.bvid = self.get_aid()

            case "BV":
                self.bvid = self.get_bvid()

        self.get_video_info()

        episode_parser = VideoEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def get_video_info(self):
        params = {
            "bvid": self.bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_category_name(self):
        # 投稿视频
        return "USER_UPLOADS"
    