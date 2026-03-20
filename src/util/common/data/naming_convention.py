convention_type_map = {
    "NORMAL": 11,
    "PART": 12,
    "COLLECTION": 13,
    "BANGUMI": 20,
    "CHEESE": 30
}

reversed_convention_type_map = {v: k for k, v in convention_type_map.items()}

class VariableListFactory:
    def __init__(self):
        pass

    def build(self, type):
        match type:
            case 11:
                return self._base_variable + self._normal_variable
            
            case 12:
                return self._base_variable + self._part_variable
            
            case 13:
                return self._base_variable + self._collection_variable
            
            case 20:
                return self._base_variable + self._bangumi_variable
            
            case 30:
                return self._base_variable + self._cheese_variable
        
        return 
    
    @property
    def _base_variable(self):
        return [
            {
                "name": "pub_time",
                "variable": "{pub_time:%Y-%m-%d_%H-%M-%S}",
                "description": "PUB_TIME",
                "example": "2026-03-07_12-00-00"
            },
            {
                "name": "pub_ts",
                "variable": "{pub_ts}",
                "description": "PUB_TS",
                "example": "1772841600"
            },
            {
                "name": "number",
                "variable": "{number}",
                "description": "NUMBER",
                "example": "1"
            },
            {
                "name": "uploader",
                "variable": "{uploader}",
                "description": "UPLOADER",
                "example": "UP主昵称"
            },
            {
                "name": "uploader_uid",
                "variable": "{uploader_uid}",
                "description": "UPLOADER_UID",
                "example": "12345678"
            }
        ]
    
    @property
    def _normal_variable(self):
        return [
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "115056436060087"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1sHePzWEbG"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "31809079869"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_NORMAL",
                "example": "游戏科学新作《黑神话：钟馗》先导预告"
            }
        ]
    
    @property
    def _part_variable(self):
        return [
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_PART",
                "example": "【KEY社20周年音乐专辑】Key BEST SELECTION"
            },
            {
                "name": "p",
                "variable": "{p}",
                "description": "PART_NUMBER_FOR_PART",
                "example": "4"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_PART",
                "example": "04 アルカテイル"
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "634233546"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1Rb4y1t7gc"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "442845594"
            }
        ]

    @property
    def _collection_variable(self):
        return [
            {
                "name": "collection_title",
                "variable": "{collection_title}",
                "description": "COLLECTION_TITLE",
                "example": "艾尔登法环白金攻略"
            },
            {
                "name": "section_title",
                "variable": "{section_title}",
                "description": "SECTION_TITLE_FOR_COLLECTION",
                "example": "DLC黄金树幽影"
            },
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_COLLECTION",
                "example": "全收集、全流程、全剧情攻略"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_COLLECTION",
                "example": "03【墓地平原-西+艾拉克河】"
            },
            {
                "name": "p",
                "variable": "{p}",
                "description": "PART_NUMBER_FOR_COLLECTION",
                "example": "3"
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "1555921697"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1r1421r78r"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "1599644073"
            }
        ]

    @property
    def _bangumi_variable(self):
        return [
            {
                "name": "series_title",
                "variable": "{series_title}",
                "description": "SERIES_TITLE_FOR_BANGUMI",
                "example": "轻音少女"
            },
            {
                "name": "season_title",
                "variable": "{season_title}",
                "description": "SEASON_TITLE",
                "example": "轻音少女 第二季"
            },
            {
                "name": "section_title",
                "variable": "{section_title}",
                "description": "SECTION_TITLE_FOR_BANGUMI_CHEESE",
                "example": "正片"
            },
            {
                "name": "episode_title",
                "variable": "{episode_title}",
                "description": "EPISODE_TITLE",
                "example": "第18话 主角！"
            },
            {
                "name": "season_number",
                "variable": "{season_number}",
                "description": "SEASON_NUMBER",
                "example": "2"
            },
            {
                "name": "episode_number",
                "variable": "{episode_number}",
                "description": "EPISODE_NUMBER",
                "example": "18"
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "849267924"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1NL4y1i7L2"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "91560482"
            },
            {
                "name": "ep_id",
                "variable": "{ep_id}",
                "description": "EP_ID",
                "example": "21296"
            },
            {
                "name": "season_id",
                "variable": "{season_id}",
                "description": "SEASON_ID",
                "example": "1173"
            }
        ]
    
    @property
    def _cheese_variable(self):
        return [
            {
                "name": "series_title",
                "variable": "{series_title}",
                "description": "SERIES_TITLE_FOR_CHEESE",
                "example": "【618限时价】清华梁爽：0-N1日语精讲高级班"
            },
            {
                "name": "section_title",
                "variable": "{section_title}",
                "description": "SECTION_TITLE_FOR_BANGUMI_CHEESE",
                "example": "先导片"
            },
            {
                "name": "episode_title",
                "variable": "{episode_title}",
                "description": "EPISODE_TITLE",
                "example": "【先导片】清华梁爽带你重新定义日语学习，教你说好、更能考好日语！"
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "315163535"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "1639897333"
            },
            {
                "name": "ep_id",
                "variable": "{ep_id}",
                "description": "EP_ID",
                "example": "158662"
            },
            {
                "name": "season_id",
                "variable": "{season_id}",
                "description": "SEASON_ID",
                "example": "4016"
            }
        ]
