#!/usr/bin/env python3
"""
测试_parse_timestamp函数
"""

import datetime

def _parse_timestamp(published_at: str) -> int:
    try:
        dt = datetime.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return 0

# 测试API返回的实际时间戳
test_cases = [
    "2020-01-10T16:04:32Z",
    "2020-01-10T16:04:31Z",
    "",
    None,
]

print("🧪 时间戳解析测试")
print("=" * 70)

for test_time in test_cases:
    if test_time is None:
        print(f"\n输入: None")
        result = _parse_timestamp(test_time or "")
    else:
        print(f"\n输入: {test_time}")
        result = _parse_timestamp(test_time)
    
    print(f"输出: {result}")
    
    if result > 0:
        dt = datetime.datetime.fromtimestamp(result)
        print(f"转换: {dt}")
    else:
        print("转换: (无效或为空)")

print("\n✅ 测试完成")
