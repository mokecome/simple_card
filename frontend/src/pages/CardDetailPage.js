import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, 
  Button, 
  Space, 
  Toast, 
  NavBar,
  Form,
  Input,
  TextArea,
  Divider,
  Loading,
  Dialog
} from 'antd-mobile';
import { 
  CheckOutline, 
  UserContactOutline, 
  EditSOutline, 
  EyeOutline,
  DeleteOutline
} from 'antd-mobile-icons';
import axios from 'axios';

const CardDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  
  // 統一的名片資料狀態 - 與OCR掃描頁面保持一致的22個欄位
  const [cardData, setCardData] = useState({
    id: '',
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
    note2: '',                   // 備註2
    
    created_at: '',              // 創建時間
    updated_at: ''               // 更新時間
  });

  // 載入名片資料
  useEffect(() => {
    loadCardData();
  }, [id]);

  // 監聽cardData變化，確保UI更新
  useEffect(() => {
    console.log('cardData已更新:', cardData);
  }, [cardData]);

  const loadCardData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/cards/${id}`);
      if (response.data && response.data.success && response.data.data) {
        // 確保所有null值轉換為空字符串，以便前端正確顯示
        const data = response.data.data;
        const processedData = {};
        Object.keys(data).forEach(key => {
          // 特殊處理：時間戳和id保持原值，其他字段轉換為字符串
          if (key === 'id' || key === 'created_at' || key === 'updated_at') {
            processedData[key] = data[key];
          } else {
            processedData[key] = data[key] || '';
          }
        });
        setCardData({ ...processedData });
      }
    } catch (error) {
      console.error('載入名片失敗:', error);
      Toast.show({
        content: '載入名片資料失敗',
        position: 'center',
        duration: 2000
      });
      navigate('/cards');
    } finally {
      setLoading(false);
    }
  };

  // 表單欄位更新處理
  const handleFieldChange = (field, value) => {
    setCardData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 切換編輯模式
  const toggleEditMode = () => {
    if (isEditing) {
      // 如果正在編輯，詢問是否取消編輯
      Dialog.confirm({
        content: '是否取消編輯？未保存的更改將會丟失。',
        onConfirm: () => {
          setIsEditing(false);
          loadCardData(); // 重新載入原始資料
        }
      });
    } else {
      setIsEditing(true);
    }
  };

  // 保存名片資料
  const handleSave = async () => {
    // 驗證必填欄位
    if (!cardData.name || !cardData.name.trim()) {
      Toast.show({
        content: '請輸入姓名',
        position: 'center',
        duration: 2000
      });
      return;
    }

    setSaving(true);
    try {
      const saveData = new FormData();
      
      // 添加名片資料 - 修復：允許空字符串以支持清空欄位
      Object.keys(cardData).forEach(key => {
        if (key !== 'id' && key !== 'created_at' && key !== 'updated_at') {
          // 使用 || '' 確保空值被轉換為空字符串
          saveData.append(key, cardData[key] || '');
        }
      });

      const response = await axios.put(`/api/v1/cards/${id}`, saveData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data && response.data.success) {
        // 直接使用PUT響應中的資料更新狀態，避免額外的GET請求
        const updatedData = response.data.data;
        const processedData = {};
        Object.keys(updatedData).forEach(key => {
          if (key === 'id' || key === 'created_at' || key === 'updated_at') {
            processedData[key] = updatedData[key];
          } else {
            processedData[key] = updatedData[key] || '';
          }
        });
        setCardData({ ...processedData });
        setIsEditing(false);
        
        Toast.show({
          content: '名片更新成功！',
          position: 'center',
          duration: 2000,
          maskClickable: false
        });
      }
    } catch (error) {
      console.error('保存失敗:', error);
      Toast.show({
        content: error.response?.data?.message || '保存失敗，請重試',
        position: 'center',
        duration: 2000
      });
    } finally {
      setSaving(false);
    }
  };

  // 刪除名片
  const handleDelete = () => {
    Dialog.confirm({
      content: '確定要刪除這張名片嗎？此操作無法復原。',
      confirmText: '刪除',
      onConfirm: async () => {
        try {
          await axios.delete(`/api/v1/cards/${id}`);
          Toast.show({
            content: '名片已刪除',
            position: 'center',
          });
          navigate('/cards');
        } catch (error) {
          console.error('刪除失敗:', error);
          Toast.show({
            content: '刪除失敗，請重試',
            position: 'center',
          });
        }
      }
    });
  };

  // 格式化日期
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="card-detail-page">
        <NavBar onBack={() => navigate('/cards')}>名片詳情</NavBar>
        <div style={{ padding: '50px', textAlign: 'center' }}>
          <Loading />
        </div>
      </div>
    );
  }

  return (
    <div className="card-detail-page">
      <NavBar 
        onBack={() => navigate('/cards')}
        right={
          <Space>
            <Button 
              size="mini" 
              color={isEditing ? 'default' : 'primary'} 
              onClick={toggleEditMode}
            >
              {isEditing ? <EyeOutline /> : <EditSOutline />}
              {isEditing ? '取消' : '編輯'}
            </Button>
          </Space>
        }
      >
        名片詳情
      </NavBar>
      
      <div className="content" style={{ padding: '16px' }}>
        {/* 名片資料顯示/編輯表單 */}
        <Card 
          title={isEditing ? "編輯名片資料" : "名片資料"} 
          extra={<UserContactOutline />} 
          style={{ marginBottom: '16px' }}
          key={`card-${cardData.id}-${cardData.updated_at}`}
        >
          <Form layout="vertical" key={`form-${cardData.id}-${cardData.updated_at}`}>
            {/* 基本資訊（中英文） */}
            <div className="form-section">
              <Divider>基本資訊</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="姓名">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入中文姓名"
                      value={cardData.name}
                      onChange={(value) => handleFieldChange('name', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.name || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="name_en">
                  {isEditing ? (
                    <Input
                      placeholder="English Name"
                      value={cardData.name_en}
                      onChange={(value) => handleFieldChange('name_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.name_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司名稱">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入公司名稱"
                      value={cardData.company_name}
                      onChange={(value) => handleFieldChange('company_name', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_name || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="company_name_en">
                  {isEditing ? (
                    <Input
                      placeholder="Company Name (English)"
                      value={cardData.company_name_en}
                      onChange={(value) => handleFieldChange('company_name_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_name_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="職位1">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入職位1"
                      value={cardData.position}
                      onChange={(value) => handleFieldChange('position', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.position || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="position_en">
                  {isEditing ? (
                    <Input
                      placeholder="Position (English)"
                      value={cardData.position_en}
                      onChange={(value) => handleFieldChange('position_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.position_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="職位2">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入職位2"
                      value={cardData.position1}
                      onChange={(value) => handleFieldChange('position1', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.position1 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="position1_en">
                  {isEditing ? (
                    <Input
                      placeholder="Position 2 (English)"
                      value={cardData.position1_en}
                      onChange={(value) => handleFieldChange('position1_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.position1_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
            </div>

            {/* 部門組織架構 */}
            <div className="form-section">
              <Divider>部門組織架構</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="部門1(單位1)">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入第一層部門"
                      value={cardData.department1}
                      onChange={(value) => handleFieldChange('department1', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department1 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="Department1">
                  {isEditing ? (
                    <Input
                      placeholder="Department Level 1"
                      value={cardData.department1_en}
                      onChange={(value) => handleFieldChange('department1_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department1_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="部門2(單位2)">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入第二層部門"
                      value={cardData.department2}
                      onChange={(value) => handleFieldChange('department2', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department2 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="Department2">
                  {isEditing ? (
                    <Input
                      placeholder="Department Level 2"
                      value={cardData.department2_en}
                      onChange={(value) => handleFieldChange('department2_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department2_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="部門3(單位3)">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入第三層部門"
                      value={cardData.department3}
                      onChange={(value) => handleFieldChange('department3', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department3 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="Department3">
                  {isEditing ? (
                    <Input
                      placeholder="Department Level 3"
                      value={cardData.department3_en}
                      onChange={(value) => handleFieldChange('department3_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department3_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
            </div>

            {/* 聯絡資訊 */}
            <div className="form-section">
              <Divider>聯絡資訊</Divider>
              
              <Form.Item label="手機">
                {isEditing ? (
                  <Input
                    placeholder="請輸入手機號碼"
                    value={cardData.mobile_phone}
                    onChange={(value) => handleFieldChange('mobile_phone', value)}
                  />
                ) : (
                  <div style={{ padding: '8px 0', fontSize: '16px' }}>
                    {cardData.mobile_phone || '-'}
                  </div>
                )}
              </Form.Item>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司電話1">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入公司電話"
                      value={cardData.company_phone1}
                      onChange={(value) => handleFieldChange('company_phone1', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_phone1 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="公司電話2">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入第二組電話"
                      value={cardData.company_phone2}
                      onChange={(value) => handleFieldChange('company_phone2', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_phone2 || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
              
              <Form.Item label="Email">
                {isEditing ? (
                  <Input
                    placeholder="請輸入Email地址"
                    value={cardData.email}
                    onChange={(value) => handleFieldChange('email', value)}
                  />
                ) : (
                  <div style={{ padding: '8px 0', fontSize: '16px' }}>
                    {cardData.email || '-'}
                  </div>
                )}
              </Form.Item>
              
              <Form.Item label="Line ID">
                {isEditing ? (
                  <Input
                    placeholder="請輸入Line ID"
                    value={cardData.line_id}
                    onChange={(value) => handleFieldChange('line_id', value)}
                  />
                ) : (
                  <div style={{ padding: '8px 0', fontSize: '16px' }}>
                    {cardData.line_id || '-'}
                  </div>
                )}
              </Form.Item>
            </div>

            {/* 地址資訊（中英文） */}
            <div className="form-section">
              <Divider>地址資訊</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司地址一">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入公司地址"
                      value={cardData.company_address1}
                      onChange={(value) => handleFieldChange('company_address1', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_address1 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="company_address1_en">
                  {isEditing ? (
                    <Input
                      placeholder="Company Address 1 (English)"
                      value={cardData.company_address1_en}
                      onChange={(value) => handleFieldChange('company_address1_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_address1_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="公司地址二">
                  {isEditing ? (
                    <Input
                      placeholder="請輸入公司地址（補充）"
                      value={cardData.company_address2}
                      onChange={(value) => handleFieldChange('company_address2', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_address2 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="company_address2_en">
                  {isEditing ? (
                    <Input
                      placeholder="Company Address 2 (English)"
                      value={cardData.company_address2_en}
                      onChange={(value) => handleFieldChange('company_address2_en', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_address2_en || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
            </div>

            {/* 備註資訊 */}
            <div className="form-section">
              <Divider>備註資訊</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="note1">
                  {isEditing ? (
                    <TextArea
                      placeholder="請輸入備註資訊"
                      rows={3}
                      value={cardData.note1}
                      onChange={(value) => handleFieldChange('note1', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px', whiteSpace: 'pre-wrap' }}>
                      {cardData.note1 || '-'}
                    </div>
                  )}
                </Form.Item>
                
                <Form.Item label="note2">
                  {isEditing ? (
                    <TextArea
                      placeholder="請輸入額外備註"
                      rows={3}
                      value={cardData.note2}
                      onChange={(value) => handleFieldChange('note2', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px', whiteSpace: 'pre-wrap' }}>
                      {cardData.note2 || '-'}
                    </div>
                  )}
                </Form.Item>
              </div>
            </div>

            {/* 時間資訊 */}
            {!isEditing && (
              <div className="form-section">
                <Divider>時間資訊</Divider>
                
                <Form.Item label="創建時間">
                  <div style={{ padding: '8px 0', fontSize: '14px', color: '#999' }}>
                    {formatDate(cardData.created_at)}
                  </div>
                </Form.Item>
                
                <Form.Item label="更新時間">
                  <div style={{ padding: '8px 0', fontSize: '14px', color: '#999' }}>
                    {formatDate(cardData.updated_at)}
                  </div>
                </Form.Item>
              </div>
            )}
          </Form>
        </Card>

        {/* 操作按鈕 */}
        <Space direction="vertical" style={{ width: '100%' }}>
          {isEditing ? (
            <Button 
              color="primary" 
              size="large" 
              block 
              onClick={handleSave}
              disabled={saving}
            >
              <CheckOutline /> 保存修改
            </Button>
          ) : (
            <Button 
              color="danger" 
              size="large" 
              block 
              onClick={handleDelete}
            >
              <DeleteOutline /> 刪除名片
            </Button>
          )}
        </Space>
      </div>
    </div>
  );
};

export default CardDetailPage; 