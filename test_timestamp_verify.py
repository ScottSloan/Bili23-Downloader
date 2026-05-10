#!/usr/bin/env python3
"""
验证YouTube API时间戳完整实现
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.youtube_api import get_playlist_items

print("✅ YouTube API 时间戳验证")
print("=" * 70)

playlist_id = "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

entries = get_playlist_items(playlist_id, max_results=5)

if not entries:
    print("❌ 获取失败")
    sys.exit(1)

print(f"\n获取 {len(entries)} 个视频\n")
print("📊 数据质量检查:\n")

all_have_timestamp = True
for i, entry in enumerate(entries, 1):
    timestamp = entry.get('timestamp', 0)
    has_time = timestamp and timestamp > 0
    status = "✅" if has_time else "❌"
    
    print(f"{status} 视频{i}:")
    print(f"   标题: {entry.get('title', 'N/A')[:40]}")
    print(f"   timestamp: {timestamp}")
    
    if not has_time:
        all_have_timestamp = False

print("\n" + "=" * 70)

if all_have_timestamp:
    print("✅ 所有视频都有有效的时间戳")
    print("✅ YouTube API 时间戳功能正常")
else:
    print("⚠️  某些视频缺少时间戳")

print("\n📝 说明:")
print("  • timestamp是Unix时间戳（秒数）")
print("  • 被用于UI中显示视频发布时间")
print("  • 如果UI中仍未显示，可能需要检查UI代码")
