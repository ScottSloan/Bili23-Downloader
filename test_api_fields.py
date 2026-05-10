#!/usr/bin/env python3
"""
YouTube播放列表API字段调试
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.network.request import SyncNetWorkRequest, ResponseType
import json

YOUTUBE_API_KEY = "AIzaSyD_-BdmOovYzUBvQiVdeZHV5J6BLCwZbd4"

def debug_playlist_fields():
    """调试播放列表返回的字段"""
    playlist_id = "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
    
    print("🔍 YouTube playlistItems API 字段调试")
    print("=" * 70)
    
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet,contentDetails",
        "playlistId": playlist_id,
        "maxResults": 1,
        "key": YOUTUBE_API_KEY,
    }
    
    print(f"📡 请求参数:")
    print(f"  part: snippet,contentDetails")
    print(f"  playlistId: {playlist_id}")
    print()
    
    request = SyncNetWorkRequest(url, params=params, response_type=ResponseType.JSON, timeout=5)
    response = request.run()
    
    items = response.get("items", [])
    if not items:
        print("❌ 无法获取项目")
        return
    
    item = items[0]
    print("📊 第一个项目的完整数据结构:\n")
    print(json.dumps(item, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 70)
    print("🔎 关键字段分析:")
    
    snippet = item.get("snippet", {})
    content_details = item.get("contentDetails", {})
    
    print(f"\n[snippet] - 摘要字段:")
    for key in snippet.keys():
        value = snippet[key]
        if isinstance(value, str) and len(str(value)) > 60:
            value = str(value)[:60] + "..."
        print(f"  • {key}: {value}")
    
    print(f"\n[contentDetails] - 内容详情字段:")
    for key in content_details.keys():
        value = content_details[key]
        if isinstance(value, str) and len(str(value)) > 60:
            value = str(value)[:60] + "..."
        print(f"  • {key}: {value}")
    
    # 检查时间相关字段
    print("\n⏰ 时间相关字段检查:")
    time_fields = [
        ("snippet.publishedAt", snippet.get("publishedAt")),
        ("snippet.videoPublishedAt", snippet.get("videoPublishedAt")),
        ("contentDetails.videoPublishedAt", content_details.get("videoPublishedAt")),
    ]
    
    for field_name, value in time_fields:
        status = "✓" if value else "✗"
        print(f"  {status} {field_name}: {value}")

if __name__ == "__main__":
    debug_playlist_fields()
