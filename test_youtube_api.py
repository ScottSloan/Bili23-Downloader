#!/usr/bin/env python3
"""
YouTube播放列表API测试 - 直接测试修复
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.youtube_api import extract_playlist_id, get_playlist_items
import json
import logging

logging.basicConfig(level=logging.INFO)

# 测试URL
test_urls = [
    "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
    "https://youtube.com/playlist?list=PL1234567890",
]

print("🧪 YouTube 播放列表API测试")
print("=" * 60)

for url in test_urls:
    print(f"\n📍 URL: {url}")
    
    playlist_id = extract_playlist_id(url)
    if not playlist_id:
        print("❌ 无法提取播放列表ID")
        continue
    
    print(f"✓ 播放列表ID: {playlist_id}")
    
    print("📥 获取播放列表项目...")
    entries = get_playlist_items(playlist_id, max_results=5)
    
    if not entries:
        print("❌ 获取失败或播放列表为空")
        continue
    
    print(f"✅ 成功获取 {len(entries)} 个视频")
    
    # 显示第一个视频的结构
    if entries:
        print("\n📊 示例视频数据结构:")
        first_entry = entries[0]
        print(json.dumps(first_entry, indent=2, ensure_ascii=False))
        
        # 检查关键字段
        required_fields = ["id", "title", "thumbnail", "duration", "webpage_url", "timestamp"]
        print(f"\n✓ 字段检查:")
        for field in required_fields:
            has_field = field in first_entry
            status = "✓" if has_field else "✗"
            value = first_entry.get(field, "N/A")[:50] if isinstance(first_entry.get(field), str) else first_entry.get(field)
            print(f"  {status} {field}: {value}")
