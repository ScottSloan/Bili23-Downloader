#!/usr/bin/env python3
"""
YouTube大型播放列表测试 - 验证能否获取71个视频
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.youtube_api import get_playlist_items
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

print("🎬 YouTube 大型播放列表测试")
print("=" * 70)

# 这是一个包含71个视频的播放列表
test_playlist_id = "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

print(f"\n📍 测试播放列表 (71个视频):")
print(f"   ID: {test_playlist_id}")
print("-" * 70)

try:
    print("\n🔄 获取播放列表项目...")
    print("   参数: max_results=500 (默认值)")
    
    # 这次应该能获取全部71个视频
    entries = get_playlist_items(test_playlist_id, max_results=500)
    
    if entries:
        print(f"\n✅ 成功获取 {len(entries)} 个视频")
        
        if len(entries) >= 71:
            print("✅ 已获取全部视频！")
        else:
            print(f"⚠️  仅获取了 {len(entries)} 个，还差 {71 - len(entries)} 个")
        
        # 显示前几个和后几个视频
        print("\n📺 前3个视频:")
        for i, entry in enumerate(entries[:3], 1):
            print(f"  {i}. {entry.get('title', 'N/A')[:50]}...")
        
        print("\n📺 后3个视频:")
        for i, entry in enumerate(entries[-3:], len(entries)-2):
            print(f"  {i}. {entry.get('title', 'N/A')[:50]}...")
        
    else:
        print(f"❌ 获取失败")
        
except Exception as e:
    logger.error(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
