#!/usr/bin/env python3
"""
合集解析调试脚本
用法: python test_collection_debug.py <BVID>
"""

import sys
import json
import httpx

# 测试一个包含合集的视频
TEST_BVID = "BV1Xr421e7Gw"  # 替换为实际的合集视频BVID

def test_api(bvid=None):
    if bvid is None:
        if len(sys.argv) > 1:
            bvid = sys.argv[1]
        else:
            bvid = TEST_BVID
    
    print(f"🔍 测试视频: {bvid}")
    print("-" * 60)
    
    try:
        # 使用与项目相同的HTTP头
        headers = {
            "Referer": "https://www.bilibili.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        print(f"📡 请求URL: {url}\n")
        
        client = httpx.Client(headers=headers, follow_redirects=True, timeout=10)
        resp = client.get(url)
        
        print(f"✓ 状态码: {resp.status_code}")
        
        data = resp.json()
        print(f"✓ API返回码: {data.get('code')}")
        print(f"✓ 返回消息: {data.get('message', 'N/A')}\n")
        
        if data.get("code") == 0:
            view_data = data.get("data", {})
            print("📊 返回数据关键字段:")
            print(f"  - title: {view_data.get('title', 'N/A')}")
            print(f"  - bvid: {view_data.get('bvid', 'N/A')}")
            print(f"  - aid: {view_data.get('aid', 'N/A')}")
            
            ugc_season = view_data.get("ugc_season")
            if ugc_season:
                print(f"\n✅ 检测到合集信息:")
                print(f"  - 合集ID: {ugc_season.get('id')}")
                print(f"  - 合集标题: {ugc_season.get('title')}")
                print(f"  - 章节数: {len(ugc_season.get('sections', []))}")
                
                sections = ugc_season.get('sections', [])
                for i, section in enumerate(sections, 1):
                    episodes = section.get('episodes', [])
                    print(f"  - 章节{i}: {section.get('title')} ({len(episodes)}个视频)")
                    for j, ep in enumerate(episodes[:3], 1):  # 只显示前3个
                        print(f"    • {j}. {ep.get('title')} ({ep.get('bvid')})")
                    if len(episodes) > 3:
                        print(f"    ... 还有 {len(episodes) - 3} 个视频")
                
                print("\n💾 完整ugc_season数据:")
                print(json.dumps(ugc_season, indent=2, ensure_ascii=False)[:500] + "...")
            else:
                print(f"\n❌ 未检测到合集信息 (ugc_season为null)")
                print(f"\n💾 返回数据(前1000字):")
                print(json.dumps(view_data, indent=2, ensure_ascii=False, default=str)[:1000] + "...")
        else:
            print(f"\n❌ API返回错误")
            print(f"💾 完整响应:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        
        client.close()
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()
