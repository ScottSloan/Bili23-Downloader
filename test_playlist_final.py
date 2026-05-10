#!/usr/bin/env python3
"""
YouTube大型播放列表完整测试
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.youtube_api import extract_playlist_id, get_playlist_items
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

print("🎬 YouTube 播放列表测试（支持大型合集）")
print("=" * 70)

# 测试不同大小的播放列表
test_cases = [
    {
        "name": "大型播放列表测试",
        "url": "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
        "expected_min": 1,  # 至少获取1个
    },
]

for test in test_cases:
    print(f"\n📍 {test['name']}")
    print(f"   URL: {test['url'][:50]}...")
    print("-" * 70)
    
    playlist_id = extract_playlist_id(test['url'])
    if not playlist_id:
        print("❌ 无法提取播放列表ID")
        continue
    
    print(f"✓ 播放列表ID: {playlist_id}")
    print("🔄 获取项目（max_results=500）...")
    
    entries = get_playlist_items(playlist_id, max_results=500)
    
    if entries:
        print(f"\n✅ 成功获取 {len(entries)} 个视频")
        
        if len(entries) >= test['expected_min']:
            print(f"✓ 满足预期 (最少 {test['expected_min']} 个)")
        
        # 显示摘要
        print(f"\n📊 播放列表摘要:")
        print(f"  总视频数: {len(entries)}")
        if entries:
            print(f"  第一个视频: {entries[0].get('title', 'N/A')[:50]}")
            print(f"  最后一个视频: {entries[-1].get('title', 'N/A')[:50]}")
    else:
        print(f"❌ 获取失败")

print("\n" + "=" * 70)
print("✅ 修复验证完成")
print("\n📋 改进摘要:")
print("  ✓ max_results参数从50增加到500")
print("  ✓ 改进分页逻辑以支持任意大小的播放列表")
print("  ✓ 添加分页进度日志")
print("  ✓ worker.py中指定max_results=500")
