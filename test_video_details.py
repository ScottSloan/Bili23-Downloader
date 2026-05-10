#!/usr/bin/env python3
"""
YouTube视频详情API测试 - 获取更完整的时间信息
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.youtube_api import get_video_info
from util.network.request import SyncNetWorkRequest, ResponseType
import json

YOUTUBE_API_KEY = "AIzaSyD_-BdmOovYzUBvQiVdeZHV5J6BLCwZbd4"

def get_video_details(video_id: str) -> dict | None:
    """使用YouTube Videos API获取完整视频信息"""
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,contentDetails,statistics,fileDetails,processingDetails",
            "id": video_id,
            "key": YOUTUBE_API_KEY,
        }
        
        request = SyncNetWorkRequest(url, params=params, response_type=ResponseType.JSON, timeout=5)
        response = request.run()
        
        items = response.get("items", [])
        if not items:
            return None
        
        return items[0]
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

print("🔍 YouTube 视频详情 vs 播放列表项目 时间对比")
print("=" * 70)

# 测试视频
video_id = "0VH1Lim8gL8"

print(f"\n视频ID: {video_id}")
print("\n第1种方式: 使用Videos API")
print("-" * 70)

video_data = get_video_details(video_id)
if video_data:
    snippet = video_data.get("snippet", {})
    print(f"publishedAt: {snippet.get('publishedAt', 'N/A')}")
    print(f"完整数据:")
    print(json.dumps(snippet, indent=2, ensure_ascii=False)[:500])
else:
    print("❌ 获取失败")

print("\n第2种方式: 使用原始get_video_info")
print("-" * 70)

api_data = get_video_info(video_id)
if api_data:
    print(f"timestamp: {api_data.get('timestamp', 'N/A')}")
    for key in api_data.keys():
        print(f"  {key}: {str(api_data[key])[:60]}")
else:
    print("❌ 获取失败")

print("\n" + "=" * 70)
print("✅ 对比完成")
