import gettext

from utils.common.datetime_util import DateTime

_ = gettext.gettext

template_list = [
    {
        "type": 1,
        "category": _("投稿视频"),
        "subcategory": _("普通"),
        "link": "https://www.bilibili.com/video/BV1sHePzWEbG",
        "link_label": "BV1sHePzWEbG"
    },
    {
        "type": 2,
        "category": _("投稿视频"),
        "subcategory": _("分P"),
        "link": "https://www.bilibili.com/video/BV1Rb4y1t7gc?p=4",
        "link_label": "BV1Rb4y1t7gc P4"
    },
    {
        "type": 3,
        "category": _("投稿视频"),
        "subcategory": _("合集"),
        "link": "https://www.bilibili.com/video/BV1zA7TzLEQe",
        "link_label": "BV1zA7TzLEQe"
    },
    {
        "type": 4,
        "category": _("投稿视频"),
        "subcategory": _("互动视频"),
        "link": "https://www.bilibili.com/video/BV1k4411B7KE",
        "link_label": "BV1k4411B7KE"
    },
    {
        "type": 5,
        "category": _("剧集"),
        "subcategory": _("默认命名"),
        "link": "https://www.bilibili.com/bangumi/play/ep21280",
        "link_label": "ep21280"
    },
    {
        "type": 6,
        "category": _("剧集"),
        "subcategory": _("严格刮削命名"),
        "link": "https://www.bilibili.com/bangumi/play/ep21280",
        "link_label": "ep21280"
    },
    {
        "type": 7,
        "category": _("课程"),
        "subcategory": "-",
        "link": "https://www.bilibili.com/cheese/play/ep158662",
        "link_label": "ep158662"
    },
    {
        "type": 8,
        "category": _("个人主页"),
        "subcategory": _("文件夹名称"),
        "link": "",
        "link_label": ""
    },
    {
        "type": 9,
        "category": _("收藏夹"),
        "subcategory": _("文件夹名称"),
        "link": "",
        "link_label": ""
    }
]

preview_data = {
    0: {
        "time": DateTime.time_str_from_timestamp(DateTime.get_timestamp(), "%H-%M-%S"),
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
        "page": "",
        "title": "游戏科学新作《黑神话：钟馗》先导预告",
        "section_title": "",
        "section_title_ex": "",
        "part_title": "",
        "collection_title": "",
        "series_title": "",
        "series_title_original": "",
        "interact_title": "",
        "episode_tag": "",
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
        "page": 4,
        "title": "04 アルカテイル",
        "section_title": "",
        "section_title_ex": "",
        "part_title": "【KEY社20周年音乐专辑】Key BEST SELECTION",
        "collection_title": "",
        "series_title": "",
        "series_title_original": "",
        "interact_title": "",
        "episode_tag": "",
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
        "page": 1,
        "title": "00 重生 _ 重启",
        "section_title": "死亡之门",
        "section_title_ex": "",
        "part_title": "【单机】勿忘我 Remember Me",
        "collection_title": "单机游戏",
        "series_title": "",
        "series_title_original": "",
        "interact_title": "",
        "episode_tag": "",
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
        "page": "",
        "title": "选择出身",
        "section_title": "",
        "section_title_ex": "",
        "part_title": "",
        "collection_title": "",
        "series_title": "",
        "series_title_original": "",
        "interact_title": "【互动视频】8种结局，你怎样弄到钱？",
        "episode_tag": "",
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
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1557741600)),
        "pubtimestamp": 1557741600,
        "zone": "",
        "subzone": "",
        "page": "",
        "title": "第2话 整顿！",
        "section_title": "正片",
        "section_title_ex": "",
        "part_title": "",
        "collection_title": "",
        "series_title": "轻音少女 第二季",
        "series_title_original": "轻音少女",
        "interact_title": "",
        "episode_tag": "",
        "badge": "限免/会员/预告/付费",
        "season_num": 2,
        "episode_num": 2,
        "bangumi_type": "番剧/电影/纪录片/国创/电视剧/综艺",
        "aid": 294314920,
        "bvid": "BV11F411h7L2",
        "cid": 91559924,
        "ep_id": 21280,
        "season_id": 1173,
        "media_id": 28220988,
        "duration": 1452,
        "up_name": "哔哩哔哩番剧",
        "up_uid": 928123
    },
    6: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1557741600)),
        "pubtimestamp": 1557741600,
        "zone": "",
        "subzone": "",
        "page": "",
        "title": "第2话 整顿！",
        "section_title": "正片",
        "section_title_ex": "Season 02",
        "part_title": "",
        "collection_title": "",
        "series_title": "轻音少女 第二季",
        "series_title_original": "轻音少女",
        "interact_title": "",
        "episode_tag": "S02E02",
        "badge": "限免/会员/预告/付费",
        "season_num": 2,
        "episode_num": 2,
        "bangumi_type": "番剧/电影/纪录片/国创/电视剧/综艺",
        "aid": 294314920,
        "bvid": "BV11F411h7L2",
        "cid": 91559924,
        "ep_id": 21280,
        "season_id": 1173,
        "media_id": 28220988,
        "duration": 1452,
        "up_name": "哔哩哔哩番剧",
        "up_uid": 928123
    },
    7: {
        "pubtime": "{pubtime:%Y-%m-%d}".format(pubtime = DateTime.from_timestamp(1687748405)),
        "pubtimestamp": 1687748405,
        "zone": "",
        "subzone": "",
        "page": "",
        "title": "【先导片】清华梁爽带你重新定义日语学习，教你说好、更能考好日语！",
        "section_title": "先导片",
        "section_title_ex": "",
        "part_title": "",
        "collection_title": "",
        "series_title": "【618限时价】清华梁爽：0-N1日语精讲高级班",
        "series_title_original": "",
        "interact_title": "",
        "episode_tag": "",
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
    },
    8: {
        "up_name": "泛式",
        "up_uid": "63231"
    },
    9: {
        "favlist_name": "默认收藏夹",
        "up_name": "泛式",
        "up_uid": "63231"
    }
}

field_data = {
    "time": {
        "name": "{time:%H-%M-%S}",
        "description": "当前时间（%H-%M-%S）",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "timestamp": {
        "name": "{timestamp}",
        "description": "当前时间戳",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "pubtime": {
        "name": "{pubtime:%Y-%m-%d}",
        "description": "视频发布时间（%Y-%m-%d）",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "pubtimestamp": {
        "name": "{pubtimestamp}",
        "description": "视频发布时间戳",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "number": {
        "name": "{number}",
        "description": "序号",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "zero_padding_number": {
        "name": "{zero_padding_number}",
        "description": "补零序号",
        "type": [1, 2, 3, 4, 5, 6, 7]
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
    "page": {
        "name": "{page}",
        "description": "分P序号",
        "type": [2, 3]
    },
    "title": {
        "name": "{title}",
        "description": "视频标题",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "section_title": {
        "name": "{section_title}",
        "description": "章节标题",
        "type": [3, 5, 6, 7]
    },
    "section_title_ex": {
        "name": "{section_title_ex}",
        "description": "章节标题，正片部分显示为 Season XX",
        "type": [6]
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
        "type": [5, 6, 7]
    },
    "series_title_original": {
        "name": "{series_title_original}",
        "description": "剧集原始名称",
        "type": [5, 6]
    },
    "interact_title": {
        "name": "{interact_title}",
        "description": "互动视频总标题",
        "type": [4]
    },
    "episode_tag": {
        "name": "{episode_tag}",
        "description": "剧集标识",
        "type": [6]
    },
    "badge": {
        "name": "{badge}",
        "description": '标识',
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "season_num": {
        "name": "{season_num}",
        "description": "季编号（第 n 季）",
        "type": [5, 6]
    },
    "episode_num": {
        "name": "{episode_num}",
        "description": "集编号（第 n 集）",
        "type": [5, 6]
    },
    "bangumi_type": {
        "name": "{bangumi_type}",
        "description": "剧集类型",
        "type": [5, 6]
    },
    "aid": {
        "name": "{aid}",
        "description": "视频 av 号",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "bvid": {
        "name": "{bvid}",
        "description": "视频 BV 号",
        "type": [1, 2, 3, 4, 5, 6]
    },
    "cid": {
        "name": "{cid}",
        "description": "视频 cid",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "ep_id": {
        "name": "{ep_id}",
        "description": "视频 ep_id",
        "type": [5, 6, 7],
    },
    "season_id": {
        "name": "{season_id}",
        "description": "视频 season_id",
        "type": [5, 6, 7]
    },
    "media_id": {
        "name": "{media_id}",
        "description": "视频 media_id",
        "type": [5, 6]
    },
    "video_quality": {
        "name": "{video_quality}",
        "description": "画质",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "audio_quality": {
        "name": "{audio_quality}",
        "description": "音质",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "video_codec": {
        "name": "{video_codec}",
        "description": "编码格式",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "duration": {
        "name": "{duration}",
        "description": "视频时长，单位为秒",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "up_name": {
        "name": "{up_name}",
        "description": "UP 主名称",
        "type": [1, 2, 3, 4, 5, 6, 7]
    },
    "up_uid": {
        "name": "{up_uid}",
        "description": "UP 主 uid",
        "type": [1, 2, 3, 4, 5, 6, 7]
    }
}

field_data_folder = {
    "up_name": {
        "name": "{up_name}",
        "description": "UP 主名称",
        "type": [8, 9],
        "example": "泛式"
    },
    "up_uid": {
        "name": "{up_uid}",
        "description": "UP 主 uid",
        "type": [8, 9],
        "example": "63231"
    },
    "favlist_name": {
        "name": "{favlist_name}",
        "description": "收藏夹名称",
        "type": [9],
        "example": "默认收藏夹"
    }
}

preview_data_ex = {
    1: {
        "badge": "最新"
    },
    2: {
        "badge": "合作",
    },
    3: {
        "badge": "充电专属",
    },
    4: {
        "badge": "最新",
    },
    5: {
        "badge": "会员",
        "bangumi_type": "番剧"
    },
    6: {
        "badge": "会员",
        "bangumi_type": "番剧"
    },
    7: {
        "badge": "全集试看"
    }
}

apply_to_data = {
    1: {
        "默认": 0
    },
    2: {
        "默认": 0
    },
    3: {
        "默认": 0
    },
    4: {
        "默认": 0
    },
    5: {
        "正片": 0,
        "非正片": 1
    },
    6: {
        "正片": 0,
        "非正片": 1
    },
    7: {
        "默认": 0,
    },
}