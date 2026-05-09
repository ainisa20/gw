#!/usr/bin/env python3
"""
测试片段匹配功能
"""

import json
from fragment_matcher import get_matcher

def test_matcher():
    """测试匹配器"""
    matcher = get_matcher()

    print("=" * 60)
    print("测试片段匹配功能")
    print("=" * 60)

    test_cases = [
        {
            "name": "社保信息页面",
            "keywords": ["社保信息", "是否申请社保", "咨询电话12333"],
            "expected_id": 35
        },
        {
            "name": "税务信息页面",
            "keywords": ["多证合一", "税务信息", "是否使用发票", "财务负责人购票人"],
            "expected_id": 32
        },
        {
            "name": "公安信息页面",
            "keywords": ["公安信息", "是否免费刻章", "咨询电话84449378"],
            "expected_id": 34
        },
        {
            "name": "人脸识别验证",
            "keywords": ["人脸识别", "人脸验证中"],
            "expected_id": 45
        },
        {
            "name": "预约银行开户",
            "keywords": ["预约银行开户", "银行机构和网点", "预约账户代扣"],
            "expected_id": 40
        }
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\n测试: {test['name']}")
        print(f"关键词: {test['keywords']}")

        frag, method, score = matcher.match_hybrid(test['keywords'])

        if frag and frag.get('id') == test['expected_id']:
            print(f"✅ 通过 - 匹配到: {frag['title']} (ID: {frag['id']})")
            print(f"   方法: {method}, 分数: {score}")
            passed += 1
        else:
            print(f"❌ 失败 - 期望ID: {test['expected_id']}, 实际: {frag['id'] if frag else 'None'}")
            if frag:
                print(f"   实际匹配到: {frag['title']}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    # 测试格式化输出
    print("\n格式化输出示例:")
    frag, _, _ = matcher.match_hybrid(["社保信息", "是否申请社保"])
    if frag:
        print(matcher.format_fragment_for_ai(frag))

if __name__ == "__main__":
    test_matcher()
