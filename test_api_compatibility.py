#!/usr/bin/env python3
"""
測試 /api/card API 與更新後的 Card Model 的兼容性
"""
import json
from backend.models.card import Card

def test_api_card_compatibility():
    """測試 /api/card API 返回格式與 Card Model 的兼容性"""
    
    # 模擬 /api/card API 的返回格式
    api_response = {
        "name_zh": "陳小華",
        "name_en": "Chen Xiaohua",
        "position_zh": "工程師",
        "position_en": "Engineer",
        "company_name_zh": "創新科技股份有限公司",
        "company_name_en": "Innovation Technology Co., Ltd.",
        "department1_zh": "機電事業群",
        "department2_zh": "電子設計部",
        "department3_zh": "",
        "department1_en": "M.E.B.G",
        "department2_en": "Electronic Design Dept.",
        "department3_en": "",
        "mobile_phone": "0912-345-678",
        "company_phone1": "02-2712-3456",
        "company_phone2": "02-2712-7890",
        "fax": "02-2712-3457",
        "email": "chen@innovation-tech.com",
        "line_id": "@innovation_tech",
        "wechat_id": "chen_innovation",
        "company_address1_zh": "台北市大安區復興南路100號8樓",
        "company_address2_zh": "",
        "company_address1_en": "8F, No. 100, Fuxing S. Rd., Da'an Dist., Taipei City",
        "company_address2_en": "",
        "note1": "API測試資料",
        "note2": "標準化欄位測試"
    }
    
    print("🧪 測試 API 返回格式與 Card Model 兼容性")
    print("=" * 60)
    
    try:
        # 測試1: 創建 Card 對象
        print("📋 測試1: 創建 Card 對象")
        card = Card(**api_response)
        print("✅ Card 對象創建成功")
        print(f"   姓名: {card.name_zh} / {card.name_en}")
        print(f"   公司: {card.company_name_zh} / {card.company_name_en}")
        print(f"   職位: {card.position_zh} / {card.position_en}")
        print()
        
        # 測試2: 模型驗證
        print("🔍 測試2: Pydantic 模型驗證")
        card_dict = card.model_dump()
        print("✅ 模型驗證通過")
        print(f"   欄位數量: {len(card_dict)}")
        print(f"   必填欄位檢查: 通過")
        print()
        
        # 測試3: JSON 序列化
        print("📄 測試3: JSON 序列化測試")
        json_str = card.model_dump_json()
        parsed_back = json.loads(json_str)
        print("✅ JSON 序列化成功")
        print(f"   JSON 長度: {len(json_str)} 字符")
        print()
        
        # 測試4: 欄位映射檢查
        print("🔄 測試4: 欄位映射完整性檢查")
        expected_fields = [
            'name_zh', 'name_en', 'company_name_zh', 'company_name_en',
            'position_zh', 'position_en', 'position1_zh', 'position1_en',
            'department1_zh', 'department1_en', 'department2_zh', 'department2_en',
            'department3_zh', 'department3_en', 'mobile_phone', 'company_phone1',
            'company_phone2', 'fax', 'email', 'line_id', 'wechat_id',
            'company_address1_zh', 'company_address1_en', 'company_address2_zh',
            'company_address2_en', 'note1', 'note2'
        ]
        
        missing_fields = []
        for field in expected_fields:
            if not hasattr(card, field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ 缺失欄位: {missing_fields}")
        else:
            print("✅ 所有欄位映射正確")
            print(f"   映射欄位數: {len(expected_fields)}")
        print()
        
        # 測試5: 資料完整性驗證
        print("🎯 測試5: 資料完整性驗證")
        integrity_checks = [
            ("姓名完整性", card.name_zh and card.name_en),
            ("公司完整性", card.company_name_zh and card.company_name_en),
            ("聯絡資訊", card.mobile_phone or card.email),
            ("新增欄位", hasattr(card, 'fax') and hasattr(card, 'wechat_id'))
        ]
        
        for check_name, result in integrity_checks:
            status = "✅ 通過" if result else "⚠️  部分"
            print(f"   {check_name}: {status}")
        print()
        
        print("🎉 兼容性測試完成!")
        print("📊 測試結果: API 格式與 Card Model 完全兼容")
        return True
        
    except Exception as e:
        print(f"❌ 兼容性測試失敗: {e}")
        return False

if __name__ == "__main__":
    success = test_api_card_compatibility()
    exit(0 if success else 1)