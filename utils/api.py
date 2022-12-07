class API:
    class App:
        @staticmethod
        def website_api():
            return "https://github.com/ScottSloan/Bili23-Downloader"

        @staticmethod
        def update_api():
            return "https://scottsloan.github.io/Bili23-Downloader/update.json"

        @staticmethod
        def changelog_api():
            return "https://scottsloan.github.io/Bili23-Downloader/CHANGELOG"

        @staticmethod
        def level_api(level):
            return "https://scottsloan.github.io/Bili23-Downloader/level/level{}.png".format(level)

    class URL:
        @staticmethod
        def base_url_api():
            return "https://bilibili.com/"

        @staticmethod
        def bvid_url_api(bvid):
            return "{}/video/{}".format(API.URL.base_url_api(), bvid)
        
        @staticmethod
        def epid_url_api(epid):
            return "{}/bangumi/play/{}".format(API.URL.base_url_api(), epid)

        @staticmethod
        def danmaku_api(cid):
            return "https://api.bilibili.com/x/v1/dm/list.so?oid={}".format(cid)

        @staticmethod
        def subtitle_api(cid, bvid):
            return "https://api.bilibili.com/x/player.so?id=cid:{}&bvid={}".format(cid, bvid)

    class Video:
        @staticmethod
        def bvid_url_api(aid):
            return "https://api.bilibili.com/x/web-interface/archive/stat?aid={}".format(aid)

        @staticmethod
        def info_api(bvid):
            return "https://api.bilibili.com/x/web-interface/view?bvid={}".format(bvid)

        @staticmethod
        def download_api(bvid, cid):
            return "https://api.bilibili.com/x/player/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(bvid, cid)

    class Bangumi:
        @staticmethod
        def season_id_api(mid):
            return "https://api.bilibili.com/pgc/review/user?media_id={}".format(mid)

        @staticmethod
        def info_api(argument, value):
            return "https://api.bilibili.com/pgc/view/web/season?{}={}".format(argument, value)

        @staticmethod
        def download_api(bvid, cid):
            return "https://api.bilibili.com/pgc/player/web/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(bvid, cid)

    class Audio:
        @staticmethod
        def sid_url_api(sid):
            return "https://www.bilibili.com/audio/au{}".format(sid)

        @staticmethod
        def amid_url_api(amid):
            return "https://www.bilibili.com/audio/am{}".format(amid)

        @staticmethod
        def music_info_api(sid):
            return "https://www.bilibili.com/audio/music-service-c/web/song/info?sid={}".format(sid)

        @staticmethod
        def playlist_info_api(amid):
            return "https://www.bilibili.com/audio/music-service-c/web/song/of-menu?sid={}&pn=1&ps=100".format(amid)

        @staticmethod
        def download_api(sid):
            return "https://www.bilibili.com/audio/music-service-c/web/url?sid={}".format(sid)

    class Live:
        @staticmethod
        def info_api(id):
            return "https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?room_ids={}&req_biz=web_room_componet".format(id)
        
        @staticmethod
        def playurl_api(room_id):
            return "https://api.live.bilibili.com/xlive/web-room/v1/playUrl/playUrl?cid={}&platform=h5&otype=json&quality=1".format(room_id)
    
    class Cheese:
        @staticmethod
        def info_api(argument, value):
            return "https://api.bilibili.com/pugv/view/web/season?{}={}".format(argument, value)

        @staticmethod
        def download_api(avid, epid, cid):
            return "https://api.bilibili.com/pugv/player/web/playurl?avid={}&ep_id={}&cid={}".format(avid, epid, cid)
    
    class QRLogin:
        @staticmethod
        def qrcode_url_api():
            return "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"

        @staticmethod
        def qrcode_status_api(qrcode_key):
            return "https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=".format(qrcode_key)

        @staticmethod
        def user_info_api():
            return "https://api.bilibili.com/x/web-interface/nav"
