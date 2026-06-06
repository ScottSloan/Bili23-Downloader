#!/usr/bin/env python3
"""Quick test: which API returns subtitles for BV1PowazHEVj?"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from qfluentwidgets import qconfig as _qconfig
from util.common.config import config, config_path
_qconfig.load(str(config_path), config)

from util.auth.cookie import cookie_manager
cookie_manager.init_cookie_info()

from util.network.request import SyncNetWorkRequest
from pathlib import Path
api_url = 'https://api.bilibili.com/x/web-interface/nav'
req = SyncNetWorkRequest(api_url)
resp = req.run()
wbi_img = resp.get('data', {}).get('wbi_img', {})
if wbi_img.get('img_url') and wbi_img.get('sub_url'):
    config.set(config.img_key, Path(wbi_img['img_url']).stem, save=False)
    config.set(config.sub_key, Path(wbi_img['sub_url']).stem, save=False)

from util.parse.parser.base import ParserBase
base = ParserBase()
bvid = "BV1PowazHEVj"
cid = 36781688024

# Test 1: wbi/v2 (current)
params = {
    "bvid": bvid, "cid": cid,
    "dm_img_list": "[]",
    "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
    "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
    "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
}
u1 = f"https://api.bilibili.com/x/player/wbi/v2?{base.enc_wbi(params)}"
r1 = SyncNetWorkRequest(u1).run()
s1 = r1.get("data", {}).get("subtitle", {})
print(f"Test 1 (wbi/v2): code={r1.get('code')}, subtitle_keys={list(s1.keys()) if s1 else 'None'}")

# Test 2: wbi/view (used by VideoParser)
params2 = {"bvid": bvid}
u2 = f"https://api.bilibili.com/x/web-interface/wbi/view?{base.enc_wbi(params2)}"
r2 = SyncNetWorkRequest(u2).run()
s2 = r2.get("data", {}).get("subtitle", {})
print(f"Test 2 (wbi/view): code={r2.get('code')}, subtitle_keys={list(s2.keys()) if s2 else 'None'}")

# Test 3: x/player/v2 (old, no WBI)
u3 = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
r3 = SyncNetWorkRequest(u3).run()
s3 = r3.get("data", {}).get("subtitle", {})
print(f"Test 3 (player/v2): code={r3.get('code')}, subtitle_keys={list(s3.keys()) if s3 else 'None'}")

# Test 4: wbi/playurl (used by downloader)
params4 = {"bvid": bvid, "cid": cid, "qn": 0, "fnver": 0, "fnval": 4048, "fourk": 1}
u4 = f"https://api.bilibili.com/x/player/wbi/playurl?{base.enc_wbi(params4)}"
r4 = SyncNetWorkRequest(u4).run()
s4 = r4.get("data", {}).get("subtitle", {})
print(f"Test 4 (wbi/playurl): code={r4.get('code')}, subtitle_keys={list(s4.keys()) if s4 else 'None'}")

os._exit(0)
