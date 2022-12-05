class API:
    class URL:
        @staticmethod
        def get_base_url():
            return "https://bilibili.com/"

        @staticmethod
        def get_url_bvid(bvid):
            return "{}/video/{}".format(API.URL.get_base_url(), bvid)
        
        @staticmethod
        def get_url_epid(epid):
            return "{}/bangumi/play/{}".format(API.URL.get_base_url(), epid)