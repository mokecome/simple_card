import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
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
  Dialog,
  Modal,
  Tag,
  Picker
} from 'antd-mobile';
import {
  CheckOutline,
  UserContactOutline,
  EditSOutline,
  EyeOutline,
  DeleteOutline,
  PictureOutline,
  StarOutline,
  DownOutline
} from 'antd-mobile-icons';
import { Image, ImageViewer } from 'antd-mobile';
import axios from 'axios';
import CardCropEditor from '../components/CardCropEditor';

const CardDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(searchParams.get('edit') === 'true');
  const [classifying, setClassifying] = useState(false);
  const [industryPickerVisible, setIndustryPickerVisible] = useState(false);

  // 圖片編輯器狀態
  const [imageEditorVisible, setImageEditorVisible] = useState(false);
  const [cropEditorVisible, setCropEditorVisible] = useState(false);
  const [editTarget, setEditTarget] = useState('front'); // 'front' | 'back'
  const [editingImage, setEditingImage] = useState(null); // { file: File, previewUrl: string, cropCorners: array|null, croppedPreview: string|null }
  const [editLoading, setEditLoading] = useState(false);
  
  // 統一的名片資料狀態 - 與資料庫欄位名稱保持一致
  const [cardData, setCardData] = useState({
    id: '',
    // 基本資訊（中英文）
    name_zh: '',                 // 姓名(中文)
    name_en: '',                 // 英文姓名
    company_name_zh: '',         // 公司名稱(中文)
    company_name_en: '',         // 英文公司名稱
    position_zh: '',             // 職位(中文)
    position_en: '',             // 英文職位
    position1_zh: '',            // 職位1(中文)
    position1_en: '',            // 職位1(英文)
    
    // 部門組織架構（中英文，三層）
    department1_zh: '',          // 部門1(中文)
    department1_en: '',          // 部門1(英文)
    department2_zh: '',          // 部門2(中文)
    department2_en: '',          // 部門2(英文)
    department3_zh: '',          // 部門3(中文)
    department3_en: '',          // 部門3(英文)
    
    // 聯絡資訊
    mobile_phone: '',            // 手機
    company_phone1: '',          // 公司電話1
    company_phone2: '',          // 公司電話2
    email: '',                   // Email
    line_id: '',                 // Line ID
    
    // 地址資訊（中英文）
    company_address1_zh: '',     // 公司地址一(中文)
    company_address1_en: '',     // 公司地址一(英文)
    company_address2_zh: '',     // 公司地址二(中文)
    company_address2_en: '',     // 公司地址二(英文)
    
    // 備註資訊
    note1: '',                   // 備註1
    note2: '',                   // 備註2

    // 產業分類信息
    industry_category: '',       // 產業分類
    classification_confidence: null, // 分類置信度
    classification_reason: '',   // 分類原因
    classified_at: '',           // 分類時間

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
    if (!cardData.name_zh || !cardData.name_zh.trim()) {
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

      // 添加暫存的裁切座標
      if (pendingCrop.front?.corners) {
        saveData.append('front_crop_corners', JSON.stringify(pendingCrop.front.corners));
      }
      if (pendingCrop.back?.corners) {
        saveData.append('back_crop_corners', JSON.stringify(pendingCrop.back.corners));
      }

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
        setPendingCrop({ front: null, back: null });
        
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

  const industryOptions = [
    { label: '防詐', value: '防詐' },
    { label: '旅宿', value: '旅宿' },
    { label: '工業應用', value: '工業應用' },
    { label: '食品業', value: '食品業' },
    { label: '其他', value: '其他' },
  ];

  // 重新分类名片
  const handleReclassify = async () => {
    setClassifying(true);
    try {
      const response = await axios.post(`/api/v1/cards/${id}/classify`);

      if (response.data && response.data.success) {
        const { industry_category, classification_confidence, classified_at, reason } = response.data.data;

        // 更新cardData状态
        setCardData(prevData => ({
          ...prevData,
          industry_category,
          classification_confidence,
          classified_at,
          classification_reason: reason || prevData.classification_reason
        }));

        Toast.show({
          content: `已分类为: ${industry_category}`,
          position: 'center',
          duration: 2000
        });
      }
    } catch (error) {
      console.error('分类失败:', error);
      Toast.show({
        content: error.response?.data?.message || '分类失败，请重试',
        position: 'center',
        duration: 2000
      });
    } finally {
      setClassifying(false);
    }
  };

  // 圖片路徑轉換為可訪問的URL
  const getImageUrl = (imagePath) => {
    if (!imagePath) return null;

    // 處理 card_data/ 路徑
    if (imagePath.startsWith('card_data/')) {
      return `/static/${imagePath}`;
    }
    // 處理 output/card_images/ 路徑
    if (imagePath.startsWith('output/card_images/')) {
      return `/static/uploads/${imagePath.replace('output/card_images/', '')}`;
    }
    return imagePath;
  };

  // 格式化日期（後端存的是 UTC，前端轉成本地時區顯示）
  const formatDate = (dateString) => {
    if (!dateString) return '';
    // 後端回傳的 ISO 格式沒有帶 Z，需補上讓瀏覽器識別為 UTC
    const utcString = dateString.endsWith('Z') ? dateString : dateString + 'Z';
    const date = new Date(utcString);
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 開啟圖片編輯器
  const handleOpenImageEditor = async (side) => {
    setEditTarget(side);
    setEditLoading(true);
    setImageEditorVisible(true);

    try {
      // 取得原圖的 File 物件
      const originalPath = side === 'front' ? cardData.front_image_path : cardData.back_image_path;
      const imageUrl = getImageUrl(originalPath);
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const file = new File([blob], 'original.jpg', { type: 'image/jpeg' });

      // 取得目前的裁切座標
      const cornersStr = side === 'front' ? cardData.front_crop_corners : cardData.back_crop_corners;
      let cropCorners = null;
      if (cornersStr) {
        try { cropCorners = typeof cornersStr === 'string' ? JSON.parse(cornersStr) : cornersStr; }
        catch { cropCorners = null; }
      }

      // 取得裁切預覽
      const croppedPath = side === 'front' ? cardData.front_cropped_image_path : cardData.back_cropped_image_path;
      const croppedUrl = getImageUrl(croppedPath || originalPath);

      setEditingImage({
        file,
        previewUrl: URL.createObjectURL(file),
        cropCorners,
        croppedPreview: croppedUrl,
      });
    } catch (error) {
      console.error('載入圖片失敗:', error);
      Toast.show({ content: '載入圖片失敗', position: 'center' });
      setImageEditorVisible(false);
    } finally {
      setEditLoading(false);
    }
  };

  // 圖片編輯器 - 旋轉 90°
  const handleEditorRotate = async () => {
    if (!editingImage?.file) return;

    setEditLoading(true);
    try {
      const imageBitmap = await createImageBitmap(editingImage.file);
      const canvas = document.createElement('canvas');
      canvas.width = imageBitmap.height;
      canvas.height = imageBitmap.width;
      const ctx = canvas.getContext('2d');
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.rotate(Math.PI / 2);
      ctx.drawImage(imageBitmap, -imageBitmap.width / 2, -imageBitmap.height / 2);
      imageBitmap.close();

      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.92));
      const rotatedFile = new File([blob], editingImage.file.name, { type: 'image/jpeg' });

      // 旋轉後自動重新偵測裁切
      const formData = new FormData();
      formData.append('file', rotatedFile);
      formData.append('enhance', 'false');

      const cropResponse = await axios.post('/api/v1/cards/crop-preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      let croppedPreview = null;
      let cropCorners = null;
      if (cropResponse.data?.success && cropResponse.data?.data) {
        croppedPreview = cropResponse.data.data.cropped_preview_base64;
        cropCorners = cropResponse.data.data.corners;
      }

      setEditingImage({
        file: rotatedFile,
        previewUrl: URL.createObjectURL(rotatedFile),
        cropCorners,
        croppedPreview: croppedPreview || URL.createObjectURL(rotatedFile),
      });

      Toast.show({ content: '已旋轉 90°', position: 'center' });
    } catch (error) {
      console.error('旋轉失敗:', error);
      Toast.show({ content: '旋轉失敗', position: 'center' });
    } finally {
      setEditLoading(false);
    }
  };

  // 圖片編輯器 - 開啟裁切
  const handleEditorOpenCrop = () => {
    setCropEditorVisible(true);
  };

  // 圖片編輯器 - 裁切確認
  const handleEditorCropConfirm = async (newCorners) => {
    setCropEditorVisible(false);
    if (!editingImage?.file) return;

    setEditLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', editingImage.file);
      formData.append('corners', JSON.stringify(newCorners));
      formData.append('enhance', 'false');

      const cropResponse = await axios.post('/api/v1/cards/crop-preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (cropResponse.data?.success && cropResponse.data?.data) {
        setEditingImage(prev => ({
          ...prev,
          cropCorners: cropResponse.data.data.corners || newCorners,
          croppedPreview: cropResponse.data.data.cropped_preview_base64 || prev.croppedPreview,
        }));
      }
    } catch (error) {
      console.error('裁切預覽失敗:', error);
    } finally {
      setEditLoading(false);
    }
  };

  // 圖片編輯器 - 儲存
  const handleEditorSave = async () => {
    if (!editingImage?.file) return;

    setEditLoading(true);
    try {
      Toast.show({ content: '儲存中...', position: 'center', duration: 0 });

      // 上傳旋轉後的原圖 + 裁切座標
      const saveData = new FormData();
      saveData.append(`${editTarget}_image`, editingImage.file);
      if (editingImage.cropCorners) {
        saveData.append(`${editTarget}_crop_corners`, JSON.stringify(editingImage.cropCorners));
      }

      // 送必要的文字欄位避免被覆蓋
      const textFields = [
        'name_zh', 'name_en', 'company_name_zh', 'company_name_en',
        'position_zh', 'position_en', 'position1_zh', 'position1_en',
        'department1_zh', 'department1_en', 'department2_zh', 'department2_en',
        'department3_zh', 'department3_en',
        'mobile_phone', 'company_phone1', 'company_phone2',
        'email', 'line_id',
        'company_address1_zh', 'company_address1_en',
        'company_address2_zh', 'company_address2_en',
        'note1', 'note2',
      ];
      textFields.forEach(key => {
        if (cardData[key] !== undefined) {
          saveData.append(key, cardData[key] || '');
        }
      });

      const saveResponse = await axios.put(`/api/v1/cards/${id}`, saveData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (saveResponse.data?.success) {
        const updatedData = saveResponse.data.data;
        const processedData = {};
        Object.keys(updatedData).forEach(key => {
          if (key === 'id' || key === 'created_at' || key === 'updated_at') {
            processedData[key] = updatedData[key];
          } else {
            processedData[key] = updatedData[key] || '';
          }
        });
        setCardData({ ...processedData });
        setImageEditorVisible(false);
        setEditingImage(null);
        Toast.clear();
        Toast.show({ content: '圖片已儲存', position: 'center' });
      } else {
        Toast.clear();
        Toast.show({ content: saveResponse.data?.message || '儲存失敗', position: 'center' });
      }
    } catch (error) {
      console.error('儲存失敗:', error);
      Toast.clear();
      Toast.show({ content: `儲存失敗: ${error.response?.data?.message || error.message}`, position: 'center' });
    } finally {
      setEditLoading(false);
    }
  };

  // 圖片編輯器 - 取消
  const handleEditorCancel = () => {
    setImageEditorVisible(false);
    setEditingImage(null);
  };

  // 取得顯示用的圖片 URL
  const getDisplayImageUrl = (side) => {
    const cropped = side === 'front' ? cardData.front_cropped_image_path : cardData.back_cropped_image_path;
    const original = side === 'front' ? cardData.front_image_path : cardData.back_image_path;
    return getImageUrl(cropped || original);
  };

  // 讀取圖片
  const openImageViewer = (image) => {
    let viewer = null;
    viewer = ImageViewer.show({
      image,
      renderFooter: () => (
        <button
          type="button"
          aria-label="關閉圖片"
          onClick={(e) => {
            e.stopPropagation();
            viewer?.close();
          }}
          style={{
            position: 'fixed',
            top: '16px',
            right: '16px',
            width: '32px',
            height: '32px',
            borderRadius: '16px',
            border: 'none',
            background: 'rgba(0,0,0,0.55)',
            color: '#fff',
            fontSize: '20px',
            lineHeight: '32px',
            textAlign: 'center',
            zIndex: 1000,
            cursor: 'pointer',
          }}
        >
          X
        </button>
      ),
    });
  };

  if (loading) {
    return (
      <div className="card-detail-page">
        <NavBar onBack={() => window.history.length > 1 ? navigate(-1) : navigate('/cards')}>名片詳情</NavBar>
        <div style={{ padding: '50px', textAlign: 'center' }}>
          <Loading />
        </div>
      </div>
    );
  }

  return (
    <div className="card-detail-page">
      <NavBar 
        onBack={() => window.history.length > 1 ? navigate(-1) : navigate('/cards')}
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
        {/* 名片圖片顯示 */}
        {((cardData.front_cropped_image_path || cardData.front_image_path) || (cardData.back_cropped_image_path || cardData.back_image_path)) && (
          <Card
            title="名片圖片"
            extra={<PictureOutline />}
            style={{ marginBottom: '16px' }}
          >
            <div style={{ display: 'flex', gap: '12px', flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center' }}>
              {(cardData.front_cropped_image_path || cardData.front_image_path) && (
                <div style={{ flex: '0 0 auto', width: '100%', maxWidth: '280px' }}>
                  <div style={{
                    fontSize: '13px',
                    fontWeight: 'bold',
                    marginBottom: '8px',
                    color: '#666'
                  }}>
                    正面
                  </div>
                  <Image
                    src={getDisplayImageUrl('front')}
                    fit="contain"
                    style={{
                      width: '100%',
                      height: '200px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      border: '1px solid #e8e8e8',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      backgroundColor: '#e8e8e8',
                    }}
                    onClick={() => {
                      openImageViewer(getDisplayImageUrl('front'));
                    }}
                    fallback={
                      <div style={{
                        width: '100%',
                        height: '200px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#f5f5f5',
                        borderRadius: '8px',
                        color: '#999'
                      }}>
                        <div style={{ textAlign: 'center' }}>
                          <PictureOutline fontSize={48} />
                          <div style={{ marginTop: '8px' }}>圖片載入失敗</div>
                        </div>
                      </div>
                    }
                  />
                  {cardData.front_image_path && (
                    <Button
                      size="small"
                      color="primary"
                      fill="outline"
                      style={{ marginTop: '8px', width: '100%' }}
                      onClick={() => handleOpenImageEditor('front')}
                    >
                      <EditSOutline /> 圖片編輯
                    </Button>
                  )}
                </div>
              )}
              {(cardData.back_cropped_image_path || cardData.back_image_path) && (
                <div style={{ flex: '0 0 auto', width: '100%', maxWidth: '280px' }}>
                  <div style={{
                    fontSize: '13px',
                    fontWeight: 'bold',
                    marginBottom: '8px',
                    color: '#666'
                  }}>
                    反面
                  </div>
                  <Image
                    src={getDisplayImageUrl('back')}
                    fit="contain"
                    style={{
                      width: '100%',
                      height: '200px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      border: '1px solid #e8e8e8',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      backgroundColor: '#e8e8e8',
                    }}
                    onClick={() => {
                      openImageViewer(getDisplayImageUrl('back'));
                    }}
                    fallback={
                      <div style={{
                        width: '100%',
                        height: '200px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#f5f5f5',
                        borderRadius: '8px',
                        color: '#999'
                      }}>
                        <div style={{ textAlign: 'center' }}>
                          <PictureOutline fontSize={48} />
                          <div style={{ marginTop: '8px' }}>圖片載入失敗</div>
                        </div>
                      </div>
                    }
                  />
                  {cardData.back_image_path && (
                    <Button
                      size="small"
                      color="primary"
                      fill="outline"
                      style={{ marginTop: '8px', width: '100%' }}
                      onClick={() => handleOpenImageEditor('back')}
                    >
                      <EditSOutline /> 圖片編輯
                    </Button>
                  )}
                </div>
              )}
            </div>
          </Card>
        )}

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
                      value={cardData.name_zh}
                      onChange={(value) => handleFieldChange('name_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.name_zh || '-'}
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
                      value={cardData.company_name_zh}
                      onChange={(value) => handleFieldChange('company_name_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_name_zh || '-'}
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
                      value={cardData.position_zh}
                      onChange={(value) => handleFieldChange('position_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.position_zh || '-'}
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
                      value={cardData.position1_zh}
                      onChange={(value) => handleFieldChange('position1_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.position1_zh || '-'}
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
                      value={cardData.department1_zh}
                      onChange={(value) => handleFieldChange('department1_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department1_zh || '-'}
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
                      value={cardData.department2_zh}
                      onChange={(value) => handleFieldChange('department2_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department2_zh || '-'}
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
                      value={cardData.department3_zh}
                      onChange={(value) => handleFieldChange('department3_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.department3_zh || '-'}
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
                      value={cardData.company_address1_zh}
                      onChange={(value) => handleFieldChange('company_address1_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_address1_zh || '-'}
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
                      value={cardData.company_address2_zh}
                      onChange={(value) => handleFieldChange('company_address2_zh', value)}
                    />
                  ) : (
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      {cardData.company_address2_zh || '-'}
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

            {/* 產業分類信息 */}
            <div className="form-section">
              <Divider>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <span>產業分類</span>
                  {!isEditing && (
                    <Button
                      color="primary"
                      size="small"
                      onClick={handleReclassify}
                      loading={classifying}
                      style={{ marginLeft: '12px' }}
                    >
                      <StarOutline style={{ marginRight: '4px' }} />
                      重新分類
                    </Button>
                  )}
                </div>
              </Divider>

              {isEditing ? (
                <Form.Item label="產業類別">
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div
                      onClick={() => setIndustryPickerVisible(true)}
                      style={{
                        border: '1px solid #d9d9d9',
                        borderRadius: '10px',
                        padding: '10px 14px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        backgroundColor: '#fff',
                        color: cardData.industry_category ? '#262626' : '#bfbfbf',
                        fontSize: '15px',
                        flex: '0 0 10%',
                        minWidth: '160px'
                      }}
                    >
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: '12px' }}>
                        {cardData.industry_category || '請選擇產業類別'}
                      </span>
                      <DownOutline style={{ fontSize: '14px', color: '#8c8c8c' }} />
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <Button
                        size="small"
                        fill="outline"
                        color="primary"
                        onClick={handleReclassify}
                        loading={classifying}
                      >
                        <StarOutline style={{ marginRight: '4px' }} />
                        AI 重新分類
                      </Button>
                    </div>
                  </div>
                  <Picker
                    columns={[industryOptions]}
                    visible={industryPickerVisible}
                    value={cardData.industry_category ? [cardData.industry_category] : []}
                    onClose={() => setIndustryPickerVisible(false)}
                    onConfirm={(values) => {
                      setIndustryPickerVisible(false);
                      handleFieldChange('industry_category', values?.[0] || '');
                    }}
                  />
                </Form.Item>
              ) : cardData.industry_category ? (
                <>
                  <Form.Item label="產業類別">
                    <div style={{ padding: '8px 0', fontSize: '16px' }}>
                      <Tag
                        color={
                          cardData.industry_category === '防詐' ? 'warning' :
                          cardData.industry_category === '旅宿' ? 'success' :
                          cardData.industry_category === '工業應用' ? 'primary' :
                          cardData.industry_category === '食品業' ? 'default' :
                          'default'
                        }
                        style={{ fontSize: '14px' }}
                      >
                        🏢 {cardData.industry_category}
                      </Tag>
                    </div>
                  </Form.Item>

                  {typeof cardData.classification_confidence === 'number' && (
                    <Form.Item label="置信度">
                      <div style={{ padding: '8px 0', fontSize: '14px', color: '#666' }}>
                        {(cardData.classification_confidence * 100).toFixed(1)}%
                      </div>
                    </Form.Item>
                  )}

                  {cardData.classified_at && (
                    <Form.Item label="分類時間">
                      <div style={{ padding: '8px 0', fontSize: '14px', color: '#999' }}>
                        {formatDate(cardData.classified_at)}
                      </div>
                    </Form.Item>
                  )}
                </>
              ) : (
                <div style={{ padding: '16px', textAlign: 'center', color: '#999' }}>
                  暫無產業分類信息，可手動選擇或點擊「AI 重新分類」
                </div>
              )}
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

      {/* 圖片編輯 Modal */}
      <Modal
        visible={imageEditorVisible}
        destroyOnClose
        actions={[]}
        content={
          <div style={{ padding: '8px' }}>
            <div style={{ fontSize: '16px', fontWeight: 'bold', textAlign: 'center', marginBottom: '12px' }}>
              圖片編輯 ({editTarget === 'front' ? '正面' : '反面'})
            </div>

            {/* 預覽區 */}
            {editLoading ? (
              <div style={{
                width: '100%', height: '250px',
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                background: '#f0f0f0', borderRadius: '8px', marginBottom: '12px',
              }}>
                <Loading />
                <div style={{ fontSize: '14px', color: '#666', marginTop: '12px' }}>處理中...</div>
              </div>
            ) : editingImage?.croppedPreview ? (
              <img
                src={editingImage.croppedPreview}
                alt="preview"
                style={{
                  width: '100%', maxHeight: '250px',
                  objectFit: 'contain', borderRadius: '8px',
                  marginBottom: '12px', background: '#f0f0f0',
                }}
              />
            ) : null}

            {/* 操作按鈕 */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <Button
                style={{ flex: 1 }}
                color="primary"
                fill="outline"
                disabled={editLoading || !editingImage}
                onClick={handleEditorRotate}
              >
                ↻ 旋轉 90°
              </Button>
              <Button
                style={{ flex: 1 }}
                color="warning"
                fill="outline"
                disabled={editLoading || !editingImage}
                onClick={handleEditorOpenCrop}
              >
                調整裁切
              </Button>
            </div>

            {/* 儲存/取消 */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <Button
                style={{ flex: 1 }}
                onClick={handleEditorCancel}
                disabled={editLoading}
              >
                取消
              </Button>
              <Button
                style={{ flex: 1 }}
                color="primary"
                disabled={editLoading || !editingImage}
                onClick={handleEditorSave}
              >
                儲存
              </Button>
            </div>
          </div>
        }
        onClose={handleEditorCancel}
      />

      {/* 裁切編輯器（從圖片編輯 Modal 打開） */}
      <CardCropEditor
        visible={cropEditorVisible}
        imageSrc={editingImage?.previewUrl || ''}
        initialCorners={editingImage?.cropCorners}
        onCancel={() => setCropEditorVisible(false)}
        onConfirm={handleEditorCropConfirm}
      />
    </div>
  );
};

export default CardDetailPage; 
