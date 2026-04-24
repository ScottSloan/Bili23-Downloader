from util.common import config

from urllib.parse import urlparse


class CDN:
    @staticmethod
    def get_url_list(url_list: list[str]) -> list[str]:
        filtered_url_list = CDN.filter(url_list)
        replaced_url_list = CDN.replace(filtered_url_list)

        if config.get(config.prefer_cdn_server_provider):
            # 将替换后的 URL 列表放在前面，原始 URL 列表放在后面，以便优先使用替换后的 URL
            url_list = replaced_url_list + url_list
        else:
            url_list = url_list + replaced_url_list

        # 去重并保持顺序
        return list(dict.fromkeys(url_list))
    
    @staticmethod
    def filter(url_list: list[str]) -> list[str]:
        # 过滤 pcdn、mcdn 等劣质链接
        filtered_url_list = []

        for url in url_list:
            if "szbdyd.com" in url or "mcdn" in url:
                continue

            filtered_url_list.append(url)

        return filtered_url_list

    @staticmethod
    def replace(url_list: list[str]) -> list[str]:
        new_url_list = []

        for url in url_list:
            for entry in config.get(config.cdn_server_list):
                node = entry.get("host")

                new_url = CDN.replace_netloc(url, node)
                new_url_list.append(new_url)

        return new_url_list
    
    @staticmethod
    def replace_netloc(url: str, new_netloc: str) -> str:
        parsed_url = urlparse(url)

        if new_netloc == parsed_url.netloc:
            return url

        new_parsed_url = parsed_url._replace(netloc = new_netloc)

        return new_parsed_url.geturl()