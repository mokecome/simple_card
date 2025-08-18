import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  Button, 
  Space, 
  Toast, 
  NavBar,
  Form,
  Input,
  TextArea,
  Divider
} from 'antd-mobile';
import { CheckOutline, UserContactOutline } from 'antd-mobile-icons';
import { createCard } from '../api/cards';
import { showSuccess, showError } from '../utils/errorHandler';

const AddCardPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  
  // 統一的名片資料狀態 - 與OCR掃描頁面保持一致的22個欄位
  const [cardData, setCardData] = useState({
    // 基本資訊（中英文）
    name: '',                    // 姓名
    name_en: '',                 // 英文姓名
    company_name: '',            // 公司名稱
    company_name_en: '',         // 英文公司名稱
    position: '',                // 職位
    position_en: '',             // 英文職位
    position1: '',               // 職位1(中文)
    position1_en: '',            // 職位1(英文)
    
    // 部門組織架構（中英文，三層）
    department1: '',             // 部門1(中文)
    department1_en: '',          // 部門1(英文)
    department2: '',             // 部門2(中文)
    department2_en: '',          // 部門2(英文)
    department3: '',             // 部門3(中文)
    department3_en: '',          // 部門3(英文)
    
    // 聯絡資訊
    mobile_phone: '',            // 手機
    company_phone1: '',          // 公司電話1
    company_phone2: '',          // 公司電話2
    email: '',                   // Email
    line_id: '',                 // Line ID
    
    // 地址資訊（中英文）
    company_address1: '',        // 公司地址一(中文)
    company_address1_en: '',     // 公司地址一(英文)
    company_address2: '',        // 公司地址二(中文)
    company_address2_en: '',     // 公司地址二(英文)
    
    // 備註資訊
    note1: '',                   // 備註1
    note2: ''                    // 備註2
  });

  // 表單欄位更新處理
  const handleFieldChange = (field, value) => {
    setCardData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 保存名片資料
  const handleSave = async () => {
    // 驗證必填欄位
    if (!cardData.name.trim()) {
      showError('請輸入姓名');
      return;
    }

    // 使用ApiWrapper統一處理錯誤和加載狀態
    const saveCard = async () => {
      const saveData = new FormData();
      
      // 添加名片資料
      Object.keys(cardData).forEach(key => {
        if (cardData[key]) {
          saveData.append(key, cardData[key]);
        }
      });

      const response = await createCard(saveData);
      return response.data;
    };

    try {
      setLoading(true);
      
      await ApiWrapper.call(
        saveCard,
        { 
          action: 'create_card',
          component: 'AddCardPage',
          cardName: cardData.name 
        },
        {
          showLoading: false, // 我們自己管理loading狀態
          successMessage: '名片新增成功！'
        }
      );

      // 成功後導航到名片管理頁面
      navigate('/cards');
      
    } catch (error) {
      // ApiWrapper已經處理了錯誤顯示，這裡只需要記錄
      console.error('創建名片失敗:', error);
    } finally {
      setLoading(false);
    }
  };

  // 重置表單
  const handleReset = () => {
    setCardData({
      // 基本資訊（中英文）
      name: '',
      name_en: '',
      company_name: '',
      company_name_en: '',
      position: '',
      position_en: '',
      position1: '',
      position1_en: '',
      
      // 部門組織架構（中英文，三層）
      department1: '',
      department1_en: '',
      department2: '',
      department2_en: '',
      department3: '',
      department3_en: '',
      
      // 聯絡資訊
      mobile_phone: '',
      company_phone1: '',
      company_phone2: '',
      email: '',
      line_id: '',
      
      // 地址資訊（中英文）
      company_address1: '',
      company_address1_en: '',
      company_address2: '',
      company_address2_en: '',
      
      // 備註資訊
      note1: '',
      note2: ''
    });
    showSuccess('表單已重置');
  };

  return (
    <div className="add-card-page">
      <NavBar onBack={() => navigate('/cards')}>手動新增名片</NavBar>
      
      <div className="content" style={{ padding: '16px' }}>
        {/* 名片資料編輯表單 */}
        <Card title="名片資料" extra={<UserContactOutline />} style={{ marginBottom: '16px' }}>
          <Form layout="vertical">
            {/* 基本資訊（中英文） */}
            <div className="form-section">
              <Divider>基本資訊</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="姓名">
                  <Input
                    placeholder="請輸入中文姓名"
                    value={cardData.name}
                    onChange={(value) => handleFieldChange('name', value)}
                  />
                </Form.Item>
                
                <Form.Item label="name_en">
                  <Input
                    placeholder="English Name"
                    value={cardData.name_en}
                    onChange={(value) => handleFieldChange('name_en', value)}
                  />
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司名稱">
                  <Input
                    placeholder="請輸入公司名稱"
                    value={cardData.company_name}
                    onChange={(value) => handleFieldChange('company_name', value)}
                  />
                </Form.Item>
                
                <Form.Item label="company_name_en">
                  <Input
                    placeholder="Company Name (English)"
                    value={cardData.company_name_en}
                    onChange={(value) => handleFieldChange('company_name_en', value)}
                  />
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="職位1">
                  <Input
                    placeholder="請輸入職位1"
                    value={cardData.position}
                    onChange={(value) => handleFieldChange('position', value)}
                  />
                </Form.Item>
                
                <Form.Item label="position_en">
                  <Input
                    placeholder="Position (English)"
                    value={cardData.position_en}
                    onChange={(value) => handleFieldChange('position_en', value)}
                  />
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="職位2">
                  <Input
                    placeholder="請輸入職位2"
                    value={cardData.position1}
                    onChange={(value) => handleFieldChange('position1', value)}
                  />
                </Form.Item>
                
                <Form.Item label="position1_en">
                  <Input
                    placeholder="Position 2 (English)"
                    value={cardData.position1_en}
                    onChange={(value) => handleFieldChange('position1_en', value)}
                  />
                </Form.Item>
              </div>
            </div>

            {/* 部門組織架構 */}
            <div className="form-section">
              <Divider>部門組織架構</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="部門1(單位1)">
                  <Input
                    placeholder="請輸入第一層部門"
                    value={cardData.department1}
                    onChange={(value) => handleFieldChange('department1', value)}
                  />
                </Form.Item>
                
                <Form.Item label="Department1">
                  <Input
                    placeholder="Department Level 1"
                    value={cardData.department1_en}
                    onChange={(value) => handleFieldChange('department1_en', value)}
                  />
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="部門2(單位2)">
                  <Input
                    placeholder="請輸入第二層部門"
                    value={cardData.department2}
                    onChange={(value) => handleFieldChange('department2', value)}
                  />
                </Form.Item>
                
                <Form.Item label="Department2">
                  <Input
                    placeholder="Department Level 2"
                    value={cardData.department2_en}
                    onChange={(value) => handleFieldChange('department2_en', value)}
                  />
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="部門3(單位3)">
                  <Input
                    placeholder="請輸入第三層部門"
                    value={cardData.department3}
                    onChange={(value) => handleFieldChange('department3', value)}
                  />
                </Form.Item>
                
                <Form.Item label="Department3">
                  <Input
                    placeholder="Department Level 3"
                    value={cardData.department3_en}
                    onChange={(value) => handleFieldChange('department3_en', value)}
                  />
                </Form.Item>
              </div>
            </div>

            {/* 聯絡資訊 */}
            <div className="form-section">
              <Divider>聯絡資訊</Divider>
              
              <Form.Item label="手機">
                <Input
                  placeholder="請輸入手機號碼"
                  value={cardData.mobile_phone}
                  onChange={(value) => handleFieldChange('mobile_phone', value)}
                />
              </Form.Item>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司電話1">
                  <Input
                    placeholder="請輸入公司電話"
                    value={cardData.company_phone1}
                    onChange={(value) => handleFieldChange('company_phone1', value)}
                  />
                </Form.Item>
                
                <Form.Item label="公司電話2">
                  <Input
                    placeholder="請輸入第二組電話"
                    value={cardData.company_phone2}
                    onChange={(value) => handleFieldChange('company_phone2', value)}
                  />
                </Form.Item>
              </div>
              
              <Form.Item label="Email">
                <Input
                  placeholder="請輸入Email地址"
                  value={cardData.email}
                  onChange={(value) => handleFieldChange('email', value)}
                />
              </Form.Item>
              
              <Form.Item label="Line ID">
                <Input
                  placeholder="請輸入Line ID"
                  value={cardData.line_id}
                  onChange={(value) => handleFieldChange('line_id', value)}
                />
              </Form.Item>
            </div>

            {/* 地址資訊（中英文） */}
            <div className="form-section">
              <Divider>地址資訊</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司地址一">
                  <Input
                    placeholder="請輸入公司地址"
                    value={cardData.company_address1}
                    onChange={(value) => handleFieldChange('company_address1', value)}
                  />
                </Form.Item>
                
                <Form.Item label="company_address1_en">
                  <Input
                    placeholder="Company Address 1 (English)"
                    value={cardData.company_address1_en}
                    onChange={(value) => handleFieldChange('company_address1_en', value)}
                  />
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司地址二">
                  <Input
                    placeholder="請輸入公司地址（補充）"
                    value={cardData.company_address2}
                    onChange={(value) => handleFieldChange('company_address2', value)}
                  />
                </Form.Item>
                
                <Form.Item label="company_address2_en">
                  <Input
                    placeholder="Company Address 2 (English)"
                    value={cardData.company_address2_en}
                    onChange={(value) => handleFieldChange('company_address2_en', value)}
                  />
                </Form.Item>
              </div>
            </div>

            {/* 備註資訊 */}
            <div className="form-section">
              <Divider>備註資訊</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="note1">
                  <TextArea
                    placeholder="請輸入備註資訊"
                    rows={3}
                    value={cardData.note1}
                    onChange={(value) => handleFieldChange('note1', value)}
                  />
                </Form.Item>
                
                <Form.Item label="note2">
                  <TextArea
                    placeholder="請輸入額外備註"
                    rows={3}
                    value={cardData.note2}
                    onChange={(value) => handleFieldChange('note2', value)}
                  />
                </Form.Item>
              </div>
            </div>
          </Form>
        </Card>

        {/* 操作按鈕 */}
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button 
            color="primary" 
            size="large" 
            block 
            onClick={handleSave}
            disabled={loading}
          >
            <CheckOutline /> 保存名片
          </Button>
          <Button 
            color="default" 
            size="large" 
            block 
            onClick={handleReset}
            disabled={loading}
          >
            重置表單
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default AddCardPage; 