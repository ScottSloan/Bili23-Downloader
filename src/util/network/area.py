from ..common._json import loads
from ..common.config import config
from ..common.enum import Area

import logging

logger = logging.getLogger(__name__)

# 用 B 站自家的 IP 归属查询接口，而不是第三方 IP 库。理由不是"它能查到地理位置"，
# 而是它的口径与本项目真正关心的那件事完全一致：CDN 探测走的是同一套代理配置，
# 用户若把 B 站域名也代理出去，这个接口会与 playurl、CDN 请求一起被同一套规则
# 导向同一个出口。第三方库拿到的出口未必与下载链路相同
AREA_ZONE_API = "https://api.bilibili.com/x/web-interface/zone"

# 单次检测的硬超时。检测失败会立刻弹窗打断用户（见 MainWindow.on_area_detected），
# 所以这里收得比全局 client 紧得多，理由同 download_url.py 的探测 client
AREA_DETECT_TIMEOUT = 5

# zone 接口用电话区号标记地区。港澳台（852 / 853 / 886）与大陆一并归入 Area.CN，
# 依据的不是行政区划而是 CDN 可达性：实测香港出口访问国内节点（华为镜像 16MB 读到
# 14.04 Mbps）反而快于海外节点（aliov 仅 4.91 Mbps）。这个分组的实际作用只是决定
# 用哪一套候选列表，那就该按"哪套快"来分，而不是按"在哪儿"分
CHINA_COUNTRY_CODES = frozenset({86, 852, 853, 886})

def parse_area(data: dict) -> Area | None:
    """
    从 zone 接口的响应中判断该使用哪一套 CDN 候选列表。

    返回的是 Area 配置值，不是纯粹的地理位置 —— 港澳台与大陆同归 Area.CN，
    理由见上面 CHINA_COUNTRY_CODES 的说明。任何解析不出来的情况都返回 None
    而不是抛异常：输入是网络响应，字段缺失、类型不对都属于正常可能，
    兜底策略由调用方决定
    """
    if not isinstance(data, dict) or data.get("code") != 0:
        return None

    zone = data.get("data")

    if not isinstance(zone, dict):
        return None

    country_code = zone.get("country_code")

    # 布尔是 int 的子类，True == 1 会被误判成合法区号，因此显式排除
    if not isinstance(country_code, int) or isinstance(country_code, bool):
        return None

    return Area.CN if country_code in CHINA_COUNTRY_CODES else Area.OV

def detect_area() -> Area:
    """
    查询出口地区。请求失败或响应无法解析一律抛异常，由调用方兜底。

    这个接口带频率风控：实测密集连续请求会返回 412，拉开到 3 秒间隔后六次全部
    成功。本函数在首次启动只会调用一次，因此不加重试 —— 真失败就走"退回询问
    用户"，比起为极小概率再等一轮超时更划算。
    """
    import httpx

    # 延迟导入：request.py 顶层加载 ssl，而 ssl 在启动禁止清单里
    from .request import get_proxy_mounts, get_ssl_context

    ssl_context = get_ssl_context()

    # 刻意不复用 request.py 的全局 client：它的 transport 带 retries = 3 且 connect
    # 超时 15s，网络不通时要将近一分钟才有结论，而检测失败是要弹窗的，等不起。
    # 链接不带宽鉴权参数，也就不必掺和全局 cookiejar 的跨线程读写
    with httpx.Client(
        timeout = httpx.Timeout(AREA_DETECT_TIMEOUT, pool = AREA_DETECT_TIMEOUT),
        transport = httpx.HTTPTransport(retries = 0, verify = ssl_context),
        mounts = get_proxy_mounts(),
        follow_redirects = True,
        verify = ssl_context
    ) as client:
        response = client.get(AREA_ZONE_API, headers = _get_detect_headers())
        response.raise_for_status()

        area = parse_area(loads(response.text))

    if area is None:
        raise RuntimeError("zone 接口的响应无法解析出地区")

    return area

def _get_detect_headers() -> dict:
    return {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": config.get(config.user_agent)
    }
