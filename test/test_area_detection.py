"""
util/network/area.py 的 parse_area() —— 从 zone 接口响应判断 CDN 区域。

这个判定决定用户拿到哪一套候选 CDN 列表。判错了不会崩溃，只会让海外用户一直
在用国内节点（或反过来），且没有任何报错 —— 因此把每种输入形态都钉住。

输入是网络响应，字段缺失、类型不对都属于正常可能，全部应当返回 None 而不是
抛异常：调用方拿 None 走"退回询问用户"的兜底路径，抛异常会把这条路径炸掉。
"""

from util.network.area import parse_area
from util.common.enum import Area

import pytest


def zone_response(country_code, code = 0):
    """构造一份 zone 接口的成功响应，字段取自实测返回"""
    data = {
        "addr": "221.7.112.22",
        "country": "中国",
        "province": "重庆",
        "isp": "联通",
    }

    if country_code is not None:
        data["country_code"] = country_code

    return {"code": code, "message": "OK", "data": data}


class TestParseArea:
    def test_mainland_is_cn(self):
        assert parse_area(zone_response(86)) == Area.CN

    @pytest.mark.parametrize("country_code", [1, 44, 81, 886, 852, 853])
    def test_non_mainland_is_ov(self, country_code):
        # 852 / 853 / 886 是港澳台。SelectAreaDialog 的文案明确把它们归入
        # "Outside Mainland China"，所以它们必须落到 OV 而不是 CN
        assert parse_area(zone_response(country_code)) == Area.OV

    def test_real_mainland_response(self):
        # 实测原文（直连出口，重庆联通）
        assert parse_area({
            "code": 0,
            "message": "OK",
            "ttl": 1,
            "data": {
                "addr": "221.7.112.22",
                "country": "中国",
                "province": "重庆",
                "isp": "联通",
                "country_code": 86,
            },
        }) == Area.CN

    def test_real_hong_kong_response(self):
        # 实测原文（Clash 香港节点出口）。这条是用来钉死港澳台的：
        # B 站对香港返回 country_code = 852 而不是 86，country 也直接写着"香港"，
        # 因此不需要额外判断 province —— 直接按 852 != 86 落到 OV 即可。
        # 若哪天 B 站把港澳台也标成 86，这个用例会失败，届时才需要补 province 判断
        assert parse_area({
            "code": 0,
            "message": "OK",
            "ttl": 1,
            "data": {
                "addr": "157.254.20.4",
                "country": "香港",
                "latitude": 22.396428,
                "longitude": 114.109497,
                "zone_id": 1035993088,
                "country_code": 852,
            },
        }) == Area.OV

    def test_non_zero_code_is_none(self):
        # 接口返回业务错误（如风控）时不能拿 data 里的残留字段下结论
        assert parse_area(zone_response(86, code = -352)) is None

    def test_missing_country_code_is_none(self):
        assert parse_area(zone_response(None)) is None

    def test_data_missing_is_none(self):
        assert parse_area({"code": 0, "message": "OK"}) is None
        assert parse_area({"code": 0, "message": "OK", "data": None}) is None

    def test_data_not_dict_is_none(self):
        assert parse_area({"code": 0, "data": "1.2.3.4"}) is None

    @pytest.mark.parametrize("country_code", ["86", 86.0, [86], {"v": 86}])
    def test_non_int_country_code_is_none(self, country_code):
        # 字符串 "86" 之类的值不能靠隐式转换蒙混过关
        assert parse_area(zone_response(country_code)) is None

    def test_bool_country_code_is_none(self):
        # bool 是 int 的子类，True == 1 会被当成合法区号误判成 OV
        assert parse_area(zone_response(True)) is None
        assert parse_area(zone_response(False)) is None

    @pytest.mark.parametrize("data", [None, [], "ok", 0, 1.5, ()])
    def test_non_dict_input_is_none(self, data):
        # 响应不是 JSON 对象时（走到了非预期的接口、被劫持等）不能抛异常
        assert parse_area(data) is None
