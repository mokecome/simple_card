import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Space,
  Card,
  Input,
  Form,
  Toast,
  NavBar,
  Loading,
  Modal,
  TextArea,
  Divider
} from 'antd-mobile';
import {
  CameraOutline,
  PictureOutline,
  CheckOutline,
  CloseOutline,
  EditSOutline,
  ScanningOutline,
  LoopOutline
} from 'antd-mobile-icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { getCameraManager } from '../utils/cameraManager';
import { getDeviceType } from '../utils/deviceDetector';
import MobileCameraModal from '../components/MobileCameraModal';
import QuickTagPanel from '../components/tags/QuickTagPanel';

const ScanUploadPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [parseLoading, setParseLoading] = useState(false);

  // 圖片管理狀態
  const [frontImage, setFrontImage] = useState({
    file: null,
    preview: null,
    ocrText: '',
    parseStatus: null // 'success', 'error', 'parsing', null
  });
  const [backImage, setBackImage] = useState({
    file: null,
    preview: null,
    ocrText: '',
    parseStatus: null // 'success', 'error', 'parsing', null
  });
  const [cameraModalVisible, setCameraModalVisible] = useState(false);
  const [currentCaptureTarget, setCurrentCaptureTarget] = useState('front'); // 'front' | 'back'
  const [stream, setStream] = useState(null);

  // 新增：相機管理器和設備類型狀態
  const [cameraManager, setCameraManager] = useState(null);
  const [isMobileCameraMode, setIsMobileCameraMode] = useState(false);
  
  // 統一的名片資料狀態 - 完整22個欄位系統 (使用_zh後綴與數據庫保持一致)
  const [cardData, setCardData] = useState({
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
    note2: ''                    // 備註2
  });
  
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // 初始化相機管理器和設備檢測
  useEffect(() => {
    const initializeCamera = async () => {
      try {
        const manager = getCameraManager();
        setCameraManager(manager);

        const type = getDeviceType();
        setIsMobileCameraMode(type === 'mobile' || type === 'tablet');

        // 日誌已移除
      } catch (error) {
        // 日誌已移除
      }
    };

    initializeCamera();
  }, []);

  // 更新圖片解析狀態
  const updateImageParseStatus = useCallback((side, status) => {
    if (side === 'front') {
      setFrontImage(prev => ({ ...prev, parseStatus: status }));
    } else {
      setBackImage(prev => ({ ...prev, parseStatus: status }));
    }
  }, []);

  // 智能解析OCR文字並填充表單
  const parseAndFillOCRData = useCallback(async (ocrText, side) => {
    console.log('[DEBUG] parseAndFillOCRData called with:', { ocrText, side });
    if (!ocrText) return;
    
    const startTime = performance.now();
    
    try {
      updateImageParseStatus(side, 'parsing');
      
      // 日誌已移除
      
      // 調用後端智能解析API
      const response = await axios.post(`${API_BASE_URL}/ocr/parse-fields`, {
        ocr_text: ocrText,
        side: side
      });
      const duration = performance.now() - startTime;

      console.log('[DEBUG] OCR API Response:', response.data);

      if (response.data.success) {
        const parsedFields = response.data.parsed_fields;
        
        if (!parsedFields || Object.keys(parsedFields).length === 0) {
          console.warn('後端返回空的解析結果');
          updateImageParseStatus(side, 'error');
          Toast.show({
            content: `${side === 'front' ? '正面' : '反面'}解析結果為空，請檢查圖片內容`,
            position: 'center',
          });
          return;
        }

        console.log('[DEBUG] Before auto-assignment logic:', parsedFields);
        
        // === 中英文自動分配邏輯（後備機制）===
        // 如果OCR服務沒有正確分配中英文內容，自動重新分配
        
        // 姓名中英文自動分配
        if (parsedFields.name_zh && !parsedFields.name_en) {
          // 如果中文欄位包含純英文，移到英文欄位
          if (/^[A-Za-z .'-]+$/.test(parsedFields.name_zh)) {
            parsedFields.name_en = parsedFields.name_zh;
            parsedFields.name_zh = '';
          }
        }
        if (parsedFields.name_en && !parsedFields.name_zh) {
          // 如果英文欄位包含中文，移到中文欄位
          if (/[\u4e00-\u9fff]/.test(parsedFields.name_en)) {
            parsedFields.name_zh = parsedFields.name_en;
            parsedFields.name_en = '';
          }
        }
        
        // 公司名稱中英文自動分配
        if (parsedFields.company_name_zh && !parsedFields.company_name_en) {
          if (/^[A-Za-z0-9 .,'&()-]+$/.test(parsedFields.company_name_zh)) {
            parsedFields.company_name_en = parsedFields.company_name_zh;
            parsedFields.company_name_zh = '';
          }
        }
        if (parsedFields.company_name_en && !parsedFields.company_name_zh) {
          if (/[\u4e00-\u9fff]/.test(parsedFields.company_name_en)) {
            parsedFields.company_name_zh = parsedFields.company_name_en;
            parsedFields.company_name_en = '';
          }
        }
        
        // 職位中英文自動分配
        if (parsedFields.position_zh && !parsedFields.position_en) {
          if (/^[A-Za-z0-9 .,'&()-]+$/.test(parsedFields.position_zh)) {
            parsedFields.position_en = parsedFields.position_zh;
            parsedFields.position_zh = '';
          }
        }
        if (parsedFields.position_en && !parsedFields.position_zh) {
          if (/[\u4e00-\u9fff]/.test(parsedFields.position_en)) {
            parsedFields.position_zh = parsedFields.position_en;
            parsedFields.position_en = '';
          }
        }
        
        // 職位1中英文自動分配
        if (parsedFields.position1_zh && !parsedFields.position1_en) {
          if (/^[A-Za-z0-9 .,'&()-]+$/.test(parsedFields.position1_zh)) {
            parsedFields.position1_en = parsedFields.position1_zh;
            parsedFields.position1_zh = '';
          }
        }
        if (parsedFields.position1_en && !parsedFields.position1_zh) {
          if (/[\u4e00-\u9fff]/.test(parsedFields.position1_en)) {
            parsedFields.position1_zh = parsedFields.position1_en;
            parsedFields.position1_en = '';
          }
        }
        
        // 部門中英文自動分配
        for (let i = 1; i <= 3; i++) {
          const zhKey = `department${i}_zh`;
          const enKey = `department${i}_en`;
          
          if (parsedFields[zhKey] && !parsedFields[enKey]) {
            if (/^[A-Za-z0-9 .,'&()-]+$/.test(parsedFields[zhKey])) {
              parsedFields[enKey] = parsedFields[zhKey];
              parsedFields[zhKey] = '';
            }
          }
          if (parsedFields[enKey] && !parsedFields[zhKey]) {
            if (/[\u4e00-\u9fff]/.test(parsedFields[enKey])) {
              parsedFields[zhKey] = parsedFields[enKey];
              parsedFields[enKey] = '';
            }
          }
        }
        
        // 地址中英文自動分配
        for (let i = 1; i <= 2; i++) {
          const zhKey = `company_address${i}_zh`;
          const enKey = `company_address${i}_en`;
          
          if (parsedFields[zhKey] && !parsedFields[enKey]) {
            if (/^[A-Za-z0-9 .,'&()-\s]+$/.test(parsedFields[zhKey])) {
              parsedFields[enKey] = parsedFields[zhKey];
              parsedFields[zhKey] = '';
            }
          }
          if (parsedFields[enKey] && !parsedFields[zhKey]) {
            if (/[\u4e00-\u9fff]/.test(parsedFields[enKey])) {
              parsedFields[zhKey] = parsedFields[enKey];
              parsedFields[enKey] = '';
            }
          }
        }
        // === END 中英文自動分配邏輯 ===
        
        console.log('[DEBUG] After auto-assignment logic:', parsedFields);
        const nonEmptyFields = Object.keys(parsedFields).filter(key => parsedFields[key] && typeof parsedFields[key] === 'string' && parsedFields[key].trim() !== '');
        console.log('[DEBUG] Non-empty fields from backend:', nonEmptyFields);
        console.log('[DEBUG] Non-empty fields count:', nonEmptyFields.length);
        
        let filledFieldsCount = 0;
        setCardData(prevData => {
          const updatedData = { ...prevData };
          console.log('[DEBUG] parsedFields:', parsedFields);
          console.log('[DEBUG] prevData before update:', prevData);
          
          Object.keys(parsedFields).forEach(field => {
            const value = parsedFields[field];
            const currentValue = updatedData[field];
            const hasValue = value && typeof value === 'string' && value.trim() !== '';
            const shouldUpdate = hasValue && (!currentValue || currentValue.trim() === '');
            
            console.log(`[DEBUG] Field: ${field}, Value: "${value}", HasValue: ${hasValue}, Current: "${currentValue}", ShouldUpdate: ${shouldUpdate}`);
            
            if (shouldUpdate) {
              updatedData[field] = value.trim();
              filledFieldsCount++;
              console.log(`[DEBUG] Updated field ${field} = "${value.trim()}"`);
            }
          });
          
          console.log('[DEBUG] updatedData after update:', updatedData);
          console.log('[DEBUG] filledFieldsCount:', filledFieldsCount);
          
          // 確保計數器能正確捕獲
          setTimeout(() => {
            Toast.show({
              content: `${side === 'front' ? '正面' : '反面'}資料解析完成！已自動填入${filledFieldsCount}個欄位`,
              position: 'center',
            });
          }, 100);
          
          return updatedData;
        });
        
        // 日誌已移除
        updateImageParseStatus(side, 'success');
      } else {
        console.error('後端解析失敗', side, response.data);
        updateImageParseStatus(side, 'error');
        Toast.show({
          content: `OCR資料解析失敗: ${response.data.message || '未知錯誤'}`,
          position: 'center',
        });
      }
    } catch (error) {
      const duration = performance.now() - startTime;
      // 日誌已移除
      updateImageParseStatus(side, 'error');
      
      let errorMessage = 'OCR資料解析失敗';
      if (error.response?.status === 404) {
        errorMessage = 'OCR服務暫不可用，請稍後重試';
      } else if (error.response?.status >= 500) {
        errorMessage = '服務器錯誤，請聯繫管理員';
      } else if (!navigator.onLine) {
        errorMessage = '網絡連接異常，請檢查網絡';
      }
      
      Toast.show({
        content: errorMessage,
        position: 'center',
      });
    }
  }, [updateImageParseStatus]);

  // 執行OCR並智能解析
  const performOCR = useCallback(async (file, side) => {
    if (!file) return;
    
    setLoading(true);
    updateImageParseStatus(side, 'parsing');
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/ocr/image`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        const ocrText = response.data.text;
        
        // 更新對應面的OCR結果
        if (side === 'front') {
          setFrontImage(prev => ({ ...prev, ocrText }));
        } else {
          setBackImage(prev => ({ ...prev, ocrText }));
        }
        
        // 執行智能解析並填充表單
        await parseAndFillOCRData(ocrText, side);
        
        Toast.show({
          content: `${side === 'front' ? '正面' : '反面'}OCR識別完成！`,
          position: 'center',
        });
      } else {
        updateImageParseStatus(side, 'error');
        Toast.show({
          content: 'OCR識別失敗，請重試',
          position: 'center',
        });
      }
    } catch (error) {
      console.error('OCR錯誤', side, error.message);
      updateImageParseStatus(side, 'error');
      Toast.show({
        content: 'OCR識別失敗，請檢查網絡連接並重試',
        position: 'center',
      });
    } finally {
      setLoading(false);
    }
  }, [parseAndFillOCRData, updateImageParseStatus]);

  // 手動解析當前圖片
  const handleManualParse = useCallback(async () => {
    const currentImage = currentCaptureTarget === 'front' ? frontImage : backImage;
    
    if (!currentImage.file) {
      Toast.show({
        content: '請先拍攝或選擇圖片',
        position: 'center',
      });
      return;
    }

    if (currentImage.ocrText) {
      // 如果已有OCR文本，直接解析
      setParseLoading(true);
      try {
        await parseAndFillOCRData(currentImage.ocrText, currentCaptureTarget);
      } finally {
        setParseLoading(false);
      }
    } else {
      // 如果沒有OCR文本，執行完整的OCR流程
      await performOCR(currentImage.file, currentCaptureTarget);
    }
  }, [currentCaptureTarget, frontImage, backImage, parseAndFillOCRData, performOCR]);

  // 處理圖片上傳
  const handleImageUpload = useCallback(async (file, target = currentCaptureTarget) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      if (target === 'front') {
        setFrontImage(prev => ({ 
          ...prev, 
          file, 
          preview: e.target.result,
          parseStatus: null // 重置解析狀態
        }));
      } else {
        setBackImage(prev => ({ 
          ...prev, 
          file, 
          preview: e.target.result,
          parseStatus: null // 重置解析狀態
        }));
      }
    };
    reader.readAsDataURL(file);

    // 自動執行OCR
    await performOCR(file, target);
  }, [performOCR, currentCaptureTarget]);

  // 啟動攝像頭 - 使用新的相機管理器
  const startCamera = async (target) => {
    if (!cameraManager) {
      Toast.show({
        content: '相機管理器未初始化',
        position: 'center',
      });
      return;
    }

    setCurrentCaptureTarget(target);

    try {
      if (isMobileCameraMode) {
        // 移動端：使用全屏相機模式
        setCameraModalVisible(true);
      } else {
        // Web端：使用傳統Modal模式
        setCameraModalVisible(true);

        // 等待Modal渲染完成後啟動相機
        setTimeout(async () => {
          try {
            const mediaStream = await cameraManager.startCamera(target, {
              videoElement: videoRef.current,
              canvasElement: canvasRef.current
            });
            setStream(mediaStream);

            // 日誌已移除
          } catch (error) {
            // 日誌已移除
            setCameraModalVisible(false);
            throw error;
          }
        }, 100);
      }
    } catch (error) {
      // 日誌已移除
      Toast.show({
        content: '無法啟動攝像頭，請檢查權限設置',
        position: 'center',
      });
    }
  };

  // 停止攝像頭 - 使用新的相機管理器
  const stopCamera = () => {
    if (cameraManager) {
      cameraManager.stopCamera();
    }
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setCameraModalVisible(false);
  };

  // 拍照 - 使用新的相機管理器
  const takePhoto = async () => {
    if (!cameraManager) {
      Toast.show({
        content: '相機管理器未初始化',
        position: 'center',
      });
      return;
    }

    // 檢查相機狀態
    const status = cameraManager.getStatus();
    if (!status.isInitialized || !status.strategy || !status.strategy.isActive) {
      Toast.show({
        content: '相機未準備就緒，請重新啟動相機',
        position: 'center',
      });
      return;
    }

    try {
      // 日誌已移除

      const result = await cameraManager.takePhoto();

      if (result && result.file) {
        // 日誌已移除

        await handleImageUpload(result.file, currentCaptureTarget);
        stopCamera();

        Toast.show({
          content: '拍照成功！',
          position: 'center',
        });
      } else {
        throw new Error('拍照結果無效');
      }
    } catch (error) {
      // 日誌已移除
      Toast.show({
        content: `拍照失敗：${error.message || '請重試'}`,
        position: 'center',
      });
    }
  };

  // 移動端相機拍照完成回調
  const handleMobilePhotoTaken = async (data) => {
    if (data && data.file) {
      await handleImageUpload(data.file, currentCaptureTarget);
    }
  };

  // 相冊上傳功能（代替批量導入）
  const [uploading, setUploading] = useState(false);

  // 快速標籤面板狀態
  const [showQuickTagPanel, setShowQuickTagPanel] = useState(false);
  const [savedCardId, setSavedCardId] = useState(null);
  const [savedCardData, setSavedCardData] = useState(null);

  // 相冊上傳處理（支持單張或多張）
  const handleMultipleFileSelect = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    setUploading(true);
    
    try {
      if (files.length === 1) {
        // 單張圖片：直接上傳到當前選中的面
        Toast.show({
          content: '正在上傳圖片並進行OCR解析...',
          position: 'center',
        });

        await handleImageUpload(files[0], currentCaptureTarget);
        
        Toast.show({
          content: '圖片上傳並解析完成！',
          position: 'center',
        });
      } else {
        // 多張圖片：批量處理
        Toast.show({
          content: `開始批量上傳 ${files.length} 張圖片...`,
          position: 'center',
        });

        let successCount = 0;
        let failCount = 0;

        // 依序處理每張圖片
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          
          try {
            Toast.show({
              content: `正在處理第 ${i + 1}/${files.length} 張圖片...`,
              position: 'center',
            });

            // 為每張圖片創建新的名片記錄
            await handleImageUpload(file, 'front'); // 默認作為正面處理
            successCount++;
            
            // 延遲一下避免請求過於頻繁
            if (i < files.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 1500));
            }
          } catch (error) {
            console.error('批量處理圖片失敗', { 
              imageIndex: i + 1, 
              fileName: file.name, 
              error: error.message 
            });
            failCount++;
          }
        }

        console.info('批量上傳完成', { 
          total: files.length, 
          success: successCount, 
          failed: failCount 
        });

        Toast.show({
          content: `批量上傳完成！成功: ${successCount}張，失敗: ${failCount}張`,
          position: 'center',
        });

        // 如果有成功處理的圖片，導航到名片管理頁面查看
        if (successCount > 0) {
          setTimeout(() => {
            navigate('/cards');
          }, 2000);
        }
      }

    } catch (error) {
      console.error('相冊上傳錯誤', { 
        error: error.message, 
        fileCount: files.length 
      });
      Toast.show({
        content: '上傳失敗，請檢查網絡連接',
        position: 'center',
      });
    } finally {
      setUploading(false);
      // 清空input以便重複選擇
      event.target.value = '';
    }
  };

  // 從相冊選擇
  const selectFromGallery = (target) => {
    setCurrentCaptureTarget(target);
    fileInputRef.current?.click();
  };


  // 保存名片資料
  const handleSave = async () => {
    // 驗證必填欄位
    if (!cardData.name_zh.trim()) {
      Toast.show({
        content: '請輸入姓名',
        position: 'center',
      });
      return;
    }

    setLoading(true);
    try {
      const saveData = new FormData();
      
      // 添加名片資料
      Object.keys(cardData).forEach(key => {
        if (cardData[key]) {
          saveData.append(key, cardData[key]);
        }
      });
      
      // 添加圖片文件
      if (frontImage.file) {
        saveData.append('front_image', frontImage.file);
      }
      if (backImage.file) {
        saveData.append('back_image', backImage.file);
      }
      
      // 添加OCR原始文字
      if (frontImage.ocrText) {
        saveData.append('front_ocr_text', frontImage.ocrText);
      }
      if (backImage.ocrText) {
        saveData.append('back_ocr_text', backImage.ocrText);
      }

      const response = await axios.post(`${API_BASE_URL}/cards/`, saveData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data && response.data.success) {
        const createdCard = response.data.data;

        Toast.show({
          content: '名片保存成功！',
          position: 'center',
        });

        // 保存名片ID和數據，用於快速標籤面板
        setSavedCardId(createdCard.id);
        setSavedCardData(cardData);

        // 顯示快速標籤面板
        setShowQuickTagPanel(true);
      }
    } catch (error) {
      console.error('保存失敗', { 
        error: error.message, 
        cardData: {
          hasName: !!cardData.name_zh,
          hasCompany: !!cardData.company_name,
          hasFrontImage: !!frontImage.file,
          hasBackImage: !!backImage.file
        }
      });
      Toast.show({
        content: '保存失敗，請重試',
        position: 'center',
      });
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

  // 快速標籤面板處理函數
  const handleQuickTagPanelClose = () => {
    setShowQuickTagPanel(false);

    // 清空表單
    setCardData({
      // 基本資訊（中英文）
      name_zh: '',
      name_en: '',
      company_name_zh: '',
      company_name_en: '',
      position_zh: '',
      position_en: '',
      position1_zh: '',
      position1_en: '',

      // 部門組織架構（中英文，三層）
      department1_zh: '',
      department1_en: '',
      department2_zh: '',
      department2_en: '',
      department3_zh: '',
      department3_en: '',

      // 聯絡資訊
      mobile_phone: '',
      company_phone1: '',
      company_phone2: '',
      email: '',
      line_id: '',

      // 地址資訊（中英文）
      company_address1_zh: '',
      company_address1_en: '',
      company_address2_zh: '',
      company_address2_en: '',

      // 備註資訊
      note1: '',
      note2: ''
    });
    setFrontImage({ file: null, preview: null, ocrText: '', parseStatus: null });
    setBackImage({ file: null, preview: null, ocrText: '', parseStatus: null });

    // 導航到名片管理頁面
    navigate('/cards');
  };

  const handleTagsAdded = (tags) => {
    console.log('已添加標籤:', tags);
  };

  // 獲取解析狀態圖標和顏色
  const getParseStatusIcon = (status) => {
    switch (status) {
      case 'parsing':
        return <LoopOutline style={{ color: '#1677ff', animation: 'spin 1s linear infinite' }} />;
      case 'success':
        return <CheckOutline style={{ color: '#52c41a' }} />;
      case 'error':
        return <CloseOutline style={{ color: '#ff4d4f' }} />;
      default:
        return null;
    }
  };

  // 添加旋轉動畫樣式
  React.useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(style);
    return () => document.head.removeChild(style);
  }, []);

  return (
    <div className="scan-upload-page">
      <NavBar onBack={() => navigate(-1)}>名片資料輸入</NavBar>
      
      {loading && <Loading />}
      
      <div className="content" style={{ padding: '16px' }}>
        {/* 圖片拍攝區域 */}
        <Card title="拍攝名片" style={{ marginBottom: '16px' }}>
          <div className="image-capture-section">
            {/* 拍攝模式切換與解析操作 */}
            <div className="capture-mode-switch" style={{ marginBottom: '16px' }}>
              <Space style={{ width: '100%', justifyContent: 'center', gap: '8px' }}>
                <Button 
                  color={currentCaptureTarget === 'front' ? 'primary' : 'default'}
                  fill={currentCaptureTarget === 'front' ? 'solid' : 'outline'}
                  onClick={() => setCurrentCaptureTarget('front')}
                  style={{ flex: 1 }}
                >
                  正面
                </Button>
                <Button 
                  color={currentCaptureTarget === 'back' ? 'primary' : 'default'}
                  fill={currentCaptureTarget === 'back' ? 'solid' : 'outline'}
                  onClick={() => setCurrentCaptureTarget('back')}
                  style={{ flex: 1 }}
                >
                  反面
                </Button>
                <Button 
                  color="success" 
                  fill="outline"
                  onClick={handleManualParse}
                  disabled={(currentCaptureTarget === 'front' ? !frontImage.file : !backImage.file) || parseLoading}
                  style={{ flex: 1 }}
                >
                  {parseLoading ? <LoopOutline style={{ animation: 'spin 1s linear infinite' }} /> : <ScanningOutline />} 解析
                </Button>
              </Space>
            </div>

            {/* 單一拍攝框 */}
            <div className="single-capture-frame">
              <div className="current-side-title" style={{ marginBottom: '8px', fontSize: '14px', fontWeight: 'bold', textAlign: 'center' }}>
                當前拍攝: {currentCaptureTarget === 'front' ? '正面' : '反面'}
                {/* 解析狀態指示 */}
                {getParseStatusIcon((currentCaptureTarget === 'front' ? frontImage : backImage).parseStatus)}
              </div>
              
              {/* 顯示當前選中面的圖片 */}
              {(currentCaptureTarget === 'front' ? frontImage.preview : backImage.preview) ? (
                <img
                  src={currentCaptureTarget === 'front' ? frontImage.preview : backImage.preview}
                  alt={`名片${currentCaptureTarget === 'front' ? '正面' : '反面'}`}
                  style={{
                    width: '100%',
                    height: 'clamp(280px, 40vw, 400px)',
                    objectFit: 'cover',
                    borderRadius: '8px',
                    marginBottom: '16px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                    transition: 'all 0.3s ease'
                  }}
                />
              ) : (
                <div
                  style={{
                    width: '100%',
                    height: 'clamp(280px, 40vw, 400px)',
                    border: '2px dashed #d9d9d9',
                    borderRadius: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#999',
                    marginBottom: '16px',
                    background: '#fafafa',
                    transition: 'all 0.3s ease'
                  }}
                >
                  <CameraOutline style={{ fontSize: '64px', marginBottom: '12px', color: '#ccc' }} />
                  <div style={{ fontSize: '16px', textAlign: 'center' }}>
                    請拍攝名片{currentCaptureTarget === 'front' ? '正面' : '反面'}
                  </div>
                  <div style={{ fontSize: '14px', color: '#bbb', marginTop: '8px' }}>
                    點擊下方按鈕開始拍照
                  </div>
                </div>
              )}

              {/* 拍攝操作按鈕 */}
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                <Button 
                  color="primary" 
                  onClick={() => startCamera(currentCaptureTarget)}
                  style={{ flex: 1 }}
                >
                  <CameraOutline /> 拍照
                </Button>
                <Button 
                  color="primary" 
                  fill="outline"
                  onClick={() => selectFromGallery(currentCaptureTarget)}
                  style={{ flex: 1 }}
                >
                  <PictureOutline /> 相冊上傳
                </Button>
              </div>

              {/* 上傳進度顯示 */}
              {uploading && (
                <div style={{ marginTop: '16px', padding: '16px', background: '#f6f6f6', borderRadius: '8px' }}>
                  <div style={{ textAlign: 'center', marginBottom: '8px', fontSize: '14px', fontWeight: 'bold' }}>
                    正在上傳圖片並進行OCR解析...
                  </div>
                  <Loading />
                </div>
              )}

              {/* 拍攝狀態指示 */}
              <div className="capture-status" style={{ marginTop: '12px', textAlign: 'center' }}>
                <Space>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <div style={{ 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      backgroundColor: frontImage.preview ? '#52c41a' : '#d9d9d9' 
                    }}></div>
                    <span style={{ fontSize: '12px', color: frontImage.preview ? '#52c41a' : '#8c8c8c' }}>
                      正面 {frontImage.preview ? '已拍攝' : '未拍攝'}
                    </span>
                    {frontImage.parseStatus && getParseStatusIcon(frontImage.parseStatus)}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <div style={{ 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      backgroundColor: backImage.preview ? '#52c41a' : '#d9d9d9' 
                    }}></div>
                    <span style={{ fontSize: '12px', color: backImage.preview ? '#52c41a' : '#8c8c8c' }}>
                      反面 {backImage.preview ? '已拍攝' : '未拍攝'}
                    </span>
                    {backImage.parseStatus && getParseStatusIcon(backImage.parseStatus)}
                  </div>
                </Space>
              </div>
            </div>
          </div>
        </Card>

        {/* 統一的名片資料編輯表單 */}
        <Card title="名片資料" extra={<EditSOutline />} style={{ marginBottom: '16px' }}>
          <Form layout="vertical">
            {/* 基本資訊（中英文） */}
            <div className="form-section">
              <Divider>基本資訊</Divider>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Form.Item label="姓名">
                  <Input
                    placeholder="請輸入中文姓名"
                    value={cardData.name_zh}
                    onChange={(value) => handleFieldChange('name_zh', value)}
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
                    value={cardData.company_name_zh}
                    onChange={(value) => handleFieldChange('company_name_zh', value)}
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
                    value={cardData.position_zh}
                    onChange={(value) => handleFieldChange('position_zh', value)}
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
                    value={cardData.position1_zh}
                    onChange={(value) => handleFieldChange('position1_zh', value)}
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
                    value={cardData.department1_zh}
                    onChange={(value) => handleFieldChange('department1_zh', value)}
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
                    value={cardData.department2_zh}
                    onChange={(value) => handleFieldChange('department2_zh', value)}
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
                    value={cardData.department3_zh}
                    onChange={(value) => handleFieldChange('department3_zh', value)}
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
                    value={cardData.company_address1_zh}
                    onChange={(value) => handleFieldChange('company_address1_zh', value)}
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
                    value={cardData.company_address2_zh}
                    onChange={(value) => handleFieldChange('company_address2_zh', value)}
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
        </Space>
      </div>

      {/* 相機模態框 - 根據設備類型選擇不同的實現 */}
      {isMobileCameraMode ? (
        // 移動端：使用全屏相機組件
        <MobileCameraModal
          visible={cameraModalVisible}
          onClose={stopCamera}
          onPhotoTaken={handleMobilePhotoTaken}
          cameraManager={cameraManager}
          target={currentCaptureTarget}
        />
      ) : (
        // Web端：使用傳統Modal
        <Modal
          visible={cameraModalVisible}
          content={
            <div className="camera-modal">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                style={{
                  width: '100%',
                  height: 'clamp(350px, 50vh, 500px)',
                  objectFit: 'cover',
                  borderRadius: '8px',
                  background: '#000'
                }}
              />
              <canvas ref={canvasRef} style={{ display: 'none' }} />
              <div style={{ marginTop: '20px', textAlign: 'center' }}>
                <Space size="large">
                  <Button
                    color="primary"
                    size="large"
                    onClick={takePhoto}
                    style={{ minWidth: '100px' }}
                  >
                    <CameraOutline /> 拍照
                  </Button>
                  <Button
                    color="default"
                    size="large"
                    onClick={stopCamera}
                    style={{ minWidth: '100px' }}
                  >
                    <CloseOutline /> 取消
                  </Button>
                </Space>
              </div>
            </div>
          }
          onClose={stopCamera}
        />
      )}

      {/* 隱藏的文件選擇輸入 */}
      <input
        type="file"
        ref={fileInputRef}
        accept="image/*"
        multiple
        style={{ display: 'none' }}
        onChange={handleMultipleFileSelect}
      />

      {/* 快速標籤面板 */}
      <QuickTagPanel
        visible={showQuickTagPanel}
        cardId={savedCardId}
        cardData={savedCardData}
        onClose={handleQuickTagPanelClose}
        onTagsAdded={handleTagsAdded}
      />
    </div>
  );
};

export default ScanUploadPage; 