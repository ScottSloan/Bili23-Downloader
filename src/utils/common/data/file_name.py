from utils.common.datetime_util import DateTime

template_list = [
    {
        "type": 1,
        "category": "投稿视频",
        "subcategory": "普通",
        "link": "https://www.bilibili.com/video/BV1sHePzWEbG",
        "link_label": "BV1sHePzWEbG"
    },
    {
        "type": 2,
        "category": "投稿视频",
        "subcategory": "分P",
        "link": "https://www.bilibili.com/video/BV1Rb4y1t7gc?p=4",
        "link_label": "BV1Rb4y1t7gc P4"
    },
    {
        "type": 3,
        "category": "投稿视频",
        "subcategory": "合集",
        "link": "https://www.bilibili.com/video/BV1zA7TzLEQe",
        "link_label": "BV1zA7TzLEQe"
    },
    {
        "type": 4,
        "category": "投稿视频",
        "subcategory": "互动视频",
        "link": "https://www.bilibili.com/video/BV1k4411B7KE",
        "link_label": "BV1k4411B7KE"
    },
    {
        "type": 5,
        "category": "剧集",
        "subcategory": "-",
        "link": "https://www.bilibili.com/bangumi/play/ep693247",
        "link_label": "ep693247"
    },
    {
        "type": 6,
        "category": "课程",
        "subcategory": "-",
        "link": "https://www.bilibili.com/cheese/play/ep158662",
        "link_label": "ep158662"
    }
]

preview_data = {
    0: {
        "time": "{time:%H-%M-%S}".format(time = DateTime.now()),
        "timestamp": DateTime.get_timestamp(),
        "number": "1",
        "zero_padding_number": "01",
        "video_quality": "超清 4K",
        "audio_quality": "Hi-Res 无损",
        "video_codec": "H265",
    },
    1: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1755633699)),
        "pubtimestamp": 1755633699,
        "zone": "单机游戏",
        "subzone": "单机主机类游戏",
        "area": "",
        "page": "",
        "title": "游戏科学新作《黑神话：钟馗》先导预告",
        "section_title": "",
        "part_title": "",
        "collection_title": "",
        "series_title": "",
        "interact_title": "",
        "badge": "充电专属/最新/合作",
        "bangumi_type": "",
        "aid": 115056436060087,
        "bvid": "BV1sHePzWEbG",
        "cid": 31809079869,
        "ep_id": "",
        "season_id": "",
        "media_id": "",
        "duration": 116,
        "up_name": "黑神话",
        "up_uid": 642389251
    },
    2: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1636974121)),
        "pubtimestamp": 1636974121,
        "zone": "乐评盘点",
        "subzone": "电台·歌单",
        "area": "",
        "page": 4,
        "title": "04 アルカテイル",
        "section_title": "",
        "part_title": "【KEY社20周年音乐专辑】Key BEST SELECTION",
        "collection_title": "",
        "series_title": "",
        "interact_title": "",
        "badge": "充电专属/最新/合作",
        "bangumi_type": "",
        "aid": 634233546,
        "bvid": "BV1Rb4y1t7gc",
        "cid": 442845594,
        "ep_id": "",
        "season_id": "",
        "media_id": "",
        "duration": 290,
        "up_name": "顾兰啸",
        "up_uid": 388972231,
    },
    3: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1748699930)),
        "pubtimestamp": 1748699930,
        "zone": "单机游戏",
        "subzone": "其他游戏",
        "area": "",
        "page": 1,
        "title": "00 重生 / 重启",
        "section_title": "死亡之门",
        "part_title": "【单机】勿忘我 Remember Me",
        "collection_title": "单机游戏",
        "series_title": "",
        "interact_title": "",
        "badge": "充电专属/最新/合作",
        "bangumi_type": "",
        "aid": 114602645920814,
        "bvid": "BV1zA7TzLEQe",
        "cid": 30249781848,
        "ep_id": "",
        "season_id": "",
        "media_id": "",
        "duration": 657,
        "up_name": "补补23456",
        "up_uid": 29460173
    },
    4: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1566895636)),
        "pubtimestamp": 1566895636,
        "zone": "影视剪辑",
        "subzone": "剧情演绎",
        "area": "",
        "page": "",
        "title": "选择出身",
        "section_title": "",
        "part_title": "",
        "collection_title": "",
        "series_title": "",
        "interact_title": "【互动视频】8种结局，你怎样弄到钱？",
        "badge": "充电专属/最新/合作",
        "bangumi_type": "",
        "aid": 65584193,
        "bvid": "BV1k4411B7KE",
        "cid": 113798528,
        "ep_id": "",
        "season_id": "",
        "media_id": "",
        "duration": 10,
        "up_name": "顾不得忠和孝",
        "up_uid": 283815363
    },
    5: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1667061000)),
        "pubtimestamp": 1667061000,
        "zone": "",
        "subzone": "",
        "area": "日本",
        "page": "",
        "title": "第1话 孤独的转机",
        "section_title": "正片",
        "part_title": "",
        "collection_title": "",
        "series_title": "孤独摇滚！",
        "interact_title": "",
        "badge": "限免/会员/预告/付费",
        "bangumi_type": "番剧/电影/纪录片/国创/电视剧/综艺",
        "aid": 944573356,
        "bvid": "BV1yW4y1j7Ft",
        "cid": 875212290,
        "ep_id": 693247,
        "season_id": 43164,
        "media_id": 28339735,
        "duration": 1415,
        "up_name": "",
        "up_uid": ""
    },
    6: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1687748405)),
        "pubtimestamp": 1687748405,
        "zone": "",
        "subzone": "",
        "area": "",
        "page": "",
        "title": "【先导片】清华梁爽带你重新定义日语学习，教你说好、更能考好日语！",
        "section_title": "先导片",
        "part_title": "",
        "collection_title": "",
        "series_title": "【618限时价】清华梁爽：0-N1日语精讲高级班",
        "interact_title": "",
        "badge": "全集试看/部分试看/付费",
        "bangumi_type": "",
        "aid": 315163535,
        "bvid": "",
        "cid": 1639897333,
        "ep_id": 158662,
        "season_id": 4016,
        "media_id": "",
        "duration": 275,
        "up_name": "清华梁爽老师",
        "up_uid": 400971040
    }
}

field_data = {
    "time": {
        "name": "{time:%H-%M-%S}",
        "description": "当前时间（%H-%M-%S）",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "timestamp": {
        "name": "{timestamp}",
        "description": "当前时间戳",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "pubtime": {
        "name": "{pubtime:%Y-%m-%d}",
        "description": "视频发布时间（%Y-%m-%d）",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "pubtimestamp": {
        "name": "{pubtimestamp}",
        "description": "视频发布时间戳",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "number": {
        "name": "{number}",
        "description": "序号",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "zero_padding_number": {
        "name": "{zero_padding_number}",
        "description": "补零序号",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "zone": {
        "name": "{zone}",
        "description": "视频分区",
        "type": [1, 2, 3, 4]
    },
    "subzone": {
        "name": "{subzone}",
        "description": "视频子分区",
        "type": [1, 2, 3, 4]
    },
    "area": {
        "name": "{area}",
        "description": "地区",
        "type": [5]
    },
    "page": {
        "name": "{page}",
        "description": "分P序号",
        "type": [2, 3]
    },
    "title": {
        "name": "{title}",
        "description": "视频标题",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "section_title": {
        "name": "{section_title}",
        "description": "章节标题",
        "type": [3, 5, 6]
    },
    "part_title": {
        "name": "{part_title}",
        "description": "分节/分P总标题",
        "type": [2, 3]
    },
    "collection_title": {
        "name": "{collection_title}",
        "description": "合集标题",
        "type": [3],
    },
    "series_title": {
        "name": "{series_title}",
        "description": "剧集名称/课程名称",
        "type": [5, 6]
    },
    "interact_title": {
        "name": "{interact_title}",
        "description": "互动视频总标题",
        "type": [4]
    },
    "badge": {
        "name": "{badge}",
        "description": '剧集列表中“备注”一栏的值',
        "type": [1, 2, 3, 4, 5, 6]
    },
    "bangumi_type": {
        "name": "{bangumi_type}",
        "description": "剧集类型",
        "type": [5]
    },
    "aid": {
        "name": "{aid}",
        "description": "视频 av 号",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "bvid": {
        "name": "{bvid}",
        "description": "视频 BV 号",
        "type": [1, 2, 3, 4, 5]
    },
    "cid": {
        "name": "{cid}",
        "description": "视频 cid",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "ep_id": {
        "name": "{ep_id}",
        "description": "视频 ep_id",
        "type": [5, 6],
    },
    "season_id": {
        "name": "{season_id}",
        "description": "视频 season_id",
        "type": [5, 6]
    },
    "media_id": {
        "name": "{media_id}",
        "description": "视频 media_id",
        "type": [5]
    },
    "video_quality": {
        "name": "{video_quality}",
        "description": "视频清晰度",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "audio_quality": {
        "name": "{audio_quality}",
        "description": "音质",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "video_codec": {
        "name": "{video_codec}",
        "description": "视频编码",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "duration": {
        "name": "{duration}",
        "description": "视频时长，单位为秒",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "up_name": {
        "name": "{up_name}",
        "description": "UP 主名称",
        "type": [1, 2, 3, 4, 6]
    },
    "up_uid": {
        "name": "{up_uid}",
        "description": "UP 主 uid",
        "type": [1, 2, 3, 4, 6]
    }
}