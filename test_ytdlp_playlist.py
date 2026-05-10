#!/usr/bin/env python3
"""
yt-dlp播放列表提取测试
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from yt_dlp import YoutubeDL
import json

print("🔍 yt-dlp 播放列表提取测试")
print("=" * 70)

playlist_url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "no_write_cookies": True,
    "extract_flat": "in_playlist",
}

print(f"\nURL: {playlist_url}")
print("\n正在提取信息...")

try:
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    
    print(f"✅ 成功\n")
    
    entries = info.get("entries", [])
    print(f"获取了 {len(entries)} 个视频\n")
    
    if entries:
        print("前2个视频的详细信息:")
        for i, entry in enumerate(entries[:2], 1):
            print(f"\n视频{i}:")
            print(f"  id: {entry.get('id', 'N/A')}")
            print(f"  title: {entry.get('title', 'N/A')[:50]}")
            print(f"  timestamp: {entry.get('timestamp', 'N/A')}")
            print(f"  upload_date: {entry.get('upload_date', 'N/A')}")
            print(f"  uploaded_date: {entry.get('uploaded_date', 'N/A')}")
            
            # 检查所有包含"time"的字段
            time_fields = [k for k in entry.keys() if 'time' in k.lower() or 'date' in k.lower()]
            if time_fields:
                print(f"  时间相关字段: {time_fields}")
                for field in time_fields:
                    print(f"    - {field}: {entry.get(field, 'N/A')}")
            
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
