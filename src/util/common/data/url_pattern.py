import re


url_patterns = [
    ("video", re.compile(r"bilibili\.com/video/([a-zA-Z0-9]+)")),
    ("bangumi", re.compile(r"bilibili\.com/bangumi/(play|media)/(ss\d+|ep\d+|md\d+)")),
    ("cheese", re.compile(r"bilibili\.com/cheese/play/(ss\d+|ep\d+)")),
    #("live", re.compile(r"live\.bilibili\.com/(\d+)")),
    ("list", re.compile(r"space\.bilibili\.com/(\d+)/lists")),
    ("favlist", re.compile(r"space\.bilibili\.com/(\d+)/favlist")),
    ("favlist", re.compile(r"www.bilibili\.com/list/ml(\d+)")),
    ("space", re.compile(r"space\.bilibili\.com/(\d+)")),
    ("space", re.compile(r"www\.bilibili\.com/medialist/play/(\d+)")),
    ("list", re.compile(r"bilibili\.com/list/(\d+)")),
    ("popular", re.compile(r"bilibili\.com/v/popular")),
    ("watch_later", re.compile(r"bili23://watch_later")),
    ("history", re.compile(r"bili23://history")),
    ("festival", re.compile(r"bilibili\.com/festival")),
    ("b23", re.compile(r"(b23\.tv|bili2233\.cn)")),
    ("video", re.compile(r"(?:BV|bv|AV|av)(\w+)")),
    ("bangumi", re.compile(r"(ep[0-9]+|ss[0-9]+)|md[0-9]+"))
]
