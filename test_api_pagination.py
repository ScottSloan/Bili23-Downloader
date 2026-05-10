#!/usr/bin/env python3
"""
YouTube API分页调试
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.network.request import SyncNetWorkRequest, ResponseType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = "AIzaSyD_-BdmOovYzUBvQiVdeZHV5J6BLCwZbd4"

def debug_playlist_api():
    """调试YouTube API分页"""
    playlist_id = "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
    
    print("🔍 YouTube API 分页调试")
    print("=" * 70)
    print(f"播放列表ID: {playlist_id}\n")
    
    # 第一次请求
    print("📡 第1次API请求...")
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet,contentDetails",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }
    
    request = SyncNetWorkRequest(url, params=params, response_type=ResponseType.JSON, timeout=5)
    response = request.run()
    
    print(f"状态: {response.get('code', 'N/A')}")
    print(f"消息: {response.get('message', 'N/A')}")
    
    items = response.get("items", [])
    print(f"✓ 返回项数: {len(items)}")
    print(f"✓ 下一页令牌: {response.get('nextPageToken', 'N/A')}")
    print(f"✓ 总页数估算: {response.get('pageInfo', {}).get('totalResults', 'N/A')}")
    
    next_page_token = response.get('nextPageToken')
    if next_page_token:
        print("\n📡 第2次API请求 (下一页)...")
        params['pageToken'] = next_page_token
        
        request = SyncNetWorkRequest(url, params=params, response_type=ResponseType.JSON, timeout=5)
        response = request.run()
        
        items2 = response.get("items", [])
        print(f"✓ 返回项数: {len(items2)}")
        print(f"✓ 下一页令牌: {response.get('nextPageToken', 'N/A')}")
        
        print(f"\n累计获取: {len(items)} + {len(items2)} = {len(items) + len(items2)} 个")
    
    # 打印第一个视频的结构
    if items:
        print("\n📊 第一个视频数据:")
        item = items[0]
        snippet = item.get('snippet', {})
        print(f"  标题: {snippet.get('title', 'N/A')}")
        print(f"  状态: {snippet.get('videoOwnerChannelTitle', 'N/A')}")
        print(f"  发布时间: {snippet.get('publishedAt', 'N/A')}")

if __name__ == "__main__":
    debug_playlist_api()
