import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Button,

  Space,
  Toast,
  NavBar,
  Modal,
  Tag,
  SearchBar,
  Divider,
  Empty,
  ProgressBar,
  InfiniteScroll,
  DotLoading,
  Selector
} from 'antd-mobile';
import {
  DeleteOutline,
  EditSOutline,
  DownlandOutline,
  AddOutline,
  UserContactOutline,
  PhoneFill,
  MailOutline,
  EnvironmentOutline,
  UploadOutline,
  PictureOutline
} from 'antd-mobile-icons';
import { Image, ImageViewer } from 'antd-mobile';
import axios from 'axios';

const CardManagerPage = () => {
  const navigate = useNavigate(); 
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [filteredCards, setFilteredCards] = useState([]);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [filterStatus, setFilterStatus] = useState('all'); // 'all', 'normal', 'problem'
  const [hasMore, setHasMore] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 20;

  // 產業篩選狀態
  const [industryFilter, setIndustryFilter] = useState('全部');
  const [classifying, setClassifying] = useState(false);

  // 批量分类任务状态
  const [taskProgress, setTaskProgress] = useState(null); // {task_id, total, completed, status}
  const [progressVisible, setProgressVisible] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);
  
  // 全局統計數據 - 不受篩選影響
  const [globalStats, setGlobalStats] = useState({
    total: 0,
    normal: 0,
    problem: 0,
    industry_stats: {}
  });
  
  // 高級篩選狀態
  const [advancedFilterVisible, setAdvancedFilterVisible] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState({
    company: '',
    position: '',
    name_zh: '',
    name_en: '',
    importDateFrom: '',
    importDateTo: '',
    hasPhone: null, // null, true, false
    hasEmail: null,
    hasAddress: null
  });

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

  // 關鍵詞高亮組件
  const HighlightText = ({ text, keyword }) => {
    if (!text || !keyword) return text || '';

    const parts = text.toString().split(new RegExp(`(${keyword})`, 'gi'));
    return parts.map((part, index) =>
      part.toLowerCase() === keyword.toLowerCase() ? (
        <span key={index} style={{ backgroundColor: '#fffb8f', color: '#cf1322', fontWeight: 'bold' }}>
          {part}
        </span>
      ) : part
    );
  };

  // 檢查名片狀態（是否有重要項目缺失）
  const checkCardStatus = (card) => {
    const missingFields = [];
    
    // 檢查姓名 (中文 OR 英文)
    const name_zh = card.name_zh?.trim() || '';
    const name_en = card.name_en?.trim() || '';
    if (!name_zh && !name_en) {
      missingFields.push('姓名/英文姓名');
    }
    
    // 檢查公司名稱 (中文 OR 英文)
    const company_zh = card.company_name_zh?.trim() || '';
    const company_en = card.company_name_en?.trim() || '';
    if (!company_zh && !company_en) {
      missingFields.push('公司名稱/英文公司名稱');
    }
    
    // 檢查職位或部門 (職位或部門有其中一個即可)
    // 檢查職位
    const position_zh = card.position_zh?.trim() || '';
    const position_en = card.position_en?.trim() || '';
    const position1_zh = card.position1_zh?.trim() || '';
    const position1_en = card.position1_en?.trim() || '';
    const hasPosition = !!(position_zh || position_en || position1_zh || position1_en);
    
    // 檢查部門
    const dept1_zh = card.department1_zh?.trim() || '';
    const dept1_en = card.department1_en?.trim() || '';
    const dept2_zh = card.department2_zh?.trim() || '';
    const dept2_en = card.department2_en?.trim() || '';
    const dept3_zh = card.department3_zh?.trim() || '';
    const dept3_en = card.department3_en?.trim() || '';
    const hasDepartment = !!(dept1_zh || dept1_en || dept2_zh || dept2_en || dept3_zh || dept3_en);
    
    // 職位或部門至少要有一個
    if (!hasPosition && !hasDepartment) {
      missingFields.push('職位或部門');
    }
    
    // 檢查聯絡方式 (手機 OR 公司電話 OR Email OR Line ID，至少要有一個)
    const mobile = card.mobile_phone?.trim() || '';
    const phone1 = card.company_phone1?.trim() || '';
    const phone2 = card.company_phone2?.trim() || '';
    const email = card.email?.trim() || '';
    const lineId = card.line_id?.trim() || '';
    if (!mobile && !phone1 && !phone2 && !email && !lineId) {
      missingFields.push('聯絡方式(電話/Email/Line)');
    }

    return {
      status: missingFields.length > 0 ? 'problem' : 'normal',
      missingFields: missingFields,
      missingCount: missingFields.length
    };
  };

  // 載入全局統計數據
  const loadGlobalStats = async () => {
    try {
      console.log('正在載入全局統計數據...');
      const response = await axios.get('/api/v1/cards/stats');
      console.log('統計API響應:', response.data);

      if (response.data && response.data.success && response.data.data) {
        console.log('設置統計數據:', response.data.data);
        setGlobalStats(response.data.data);
      } else {
        console.log('統計API響應格式不正確:', response.data);
      }
    } catch (error) {
      console.error('載入統計數據失敗:', error);
      console.error('錯誤詳情:', error.response?.data);
    }
  };

  // 批量AI分类（异步）
  const handleBatchClassify = async () => {
    setClassifying(true);
    try {
      const response = await axios.post('/api/v1/cards/classify-batch', {
        card_ids: null // null 表示分类所有未分类的名片
      });

      if (response.data && response.data.success) {
        const taskData = response.data.data;

        // 如果没有需要分类的名片
        if (taskData.total === 0) {
          Toast.show({
            content: '没有需要分类的名片',
            position: 'center',
          });
          setClassifying(false);
          return;
        }

        // 保存任务信息并显示进度对话框
        setTaskProgress(taskData);
        setProgressVisible(true);

        // 开始轮询任务状态
        startPolling(taskData.task_id);
      }
    } catch (error) {
      console.error('启动批量分类失败:', error);
      Toast.show({
        content: '启动批量分类失败',
        position: 'center',
      });
      setClassifying(false);
    }
  };

  // 轮询任务状态
  const startPolling = (taskId) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/v1/cards/tasks/${taskId}`);

        if (response.data && response.data.success) {
          const taskData = response.data.data;
          setTaskProgress(taskData);

          // 如果任务已完成、失败或取消，停止轮询
          if (['completed', 'failed', 'cancelled'].includes(taskData.status)) {
            clearInterval(interval);
            setClassifying(false);

            // 显示结果
            if (taskData.status === 'completed') {
              Toast.show({
                content: `成功分类 ${taskData.success_count}/${taskData.total} 张名片`,
                position: 'center',
                duration: 3000
              });
              // 重新加载列表
              loadCards();
            } else if (taskData.status === 'failed') {
              Toast.show({
                content: `分类失败: ${taskData.error_message}`,
                position: 'center',
                duration: 3000
              });
            } else if (taskData.status === 'cancelled') {
              Toast.show({
                content: '任务已取消',
                position: 'center',
                duration: 2000
              });
            }

            // 延迟关闭进度对话框
            setTimeout(() => {
              setProgressVisible(false);
              setTaskProgress(null);
            }, 2000);
          }
        }
      } catch (error) {
        console.error('轮询任务状态失败:', error);
        clearInterval(interval);
        setClassifying(false);
        setProgressVisible(false);
        Toast.show({
          content: '获取任务状态失败',
          position: 'center',
        });
      }
    }, 2000); // 每2秒轮询一次

    setPollingInterval(interval);
  };

  // 取消任务
  const handleCancelTask = async () => {
    if (!taskProgress || !taskProgress.task_id) return;

    try {
      const response = await axios.post(`/api/v1/cards/tasks/${taskProgress.task_id}/cancel`);

      if (response.data && response.data.success) {
        Toast.show({
          content: '正在取消任务...',
          position: 'center',
        });
      }
    } catch (error) {
      console.error('取消任务失败:', error);
      Toast.show({
        content: '取消任务失败',
        position: 'center',
      });
    }
  };

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // 載入名片列表 - 真正的分頁實現
  const loadCards = async (isLoadMore = false) => {
    if (!isLoadMore) {
      setLoading(true);
      setCurrentPage(0);
      setCards([]);
      setFilteredCards([]);
    }

    try {
      const currentPageToLoad = isLoadMore ? currentPage + 1 : 0;
      const response = await axios.get('/api/v1/cards/', {
        params: {
          use_pagination: true,
          skip: currentPageToLoad * pageSize,
          limit: pageSize,
          search: searchText || undefined,
          industry: industryFilter && industryFilter !== '全部' ? industryFilter : undefined // 產業篩選
        }
      });
      
      if (response.data && response.data.success && response.data.data) {
        const { items, total, has_more } = response.data.data;
        
        if (isLoadMore) {
          setCards(prev => [...prev, ...items]);
          setFilteredCards(prev => [...prev, ...items]);
          setCurrentPage(currentPageToLoad);
        } else {
          setCards(items);
          setFilteredCards(items);
          setCurrentPage(0);
        }
        
        setHasMore(has_more);
      }
    } catch (error) {
      console.error('載入名片失敗:', error);
      Toast.show({
        content: '載入名片失敗',
        position: 'center',
      });
    } finally {
      setLoading(false);
    }
  };
  
  // 載入更多
  const loadMore = async () => {
    if (!hasMore || loading) return;
    await loadCards(true);
  };

  useEffect(() => {
    loadCards();
    loadGlobalStats(); // 載入全局統計數據
  }, []);

  // 高級篩選邏輯
  const applyAdvancedFilters = (cards) => {
    return cards.filter(card => {
      // 中文姓名篩選
      if (advancedFilters.name_zh && 
          !(card.name_zh && card.name_zh.toLowerCase().includes(advancedFilters.name_zh.toLowerCase()))) {
        return false;
      }

      // 英文姓名篩選
      if (advancedFilters.name_en && 
          !(card.name_en && card.name_en.toLowerCase().includes(advancedFilters.name_en.toLowerCase()))) {
        return false;
      }

      // 公司篩選
      if (advancedFilters.company && 
          !((card.company_name_zh && card.company_name_zh.toLowerCase().includes(advancedFilters.company.toLowerCase())) ||
            (card.company_name_en && card.company_name_en.toLowerCase().includes(advancedFilters.company.toLowerCase())))) {
        return false;
      }

      // 職位篩選
      if (advancedFilters.position && 
          !((card.position_zh && card.position_zh.toLowerCase().includes(advancedFilters.position.toLowerCase())) ||
            (card.position_en && card.position_en.toLowerCase().includes(advancedFilters.position.toLowerCase())) ||
            (card.position1_zh && card.position1_zh.toLowerCase().includes(advancedFilters.position.toLowerCase())) ||
            (card.position1_en && card.position1_en.toLowerCase().includes(advancedFilters.position.toLowerCase())))) {
        return false;
      }

      // 導入時間篩選
      if (advancedFilters.importDateFrom || advancedFilters.importDateTo) {
        const cardDate = new Date(card.created_at);
        if (advancedFilters.importDateFrom && cardDate < new Date(advancedFilters.importDateFrom)) {
          return false;
        }
        if (advancedFilters.importDateTo && cardDate > new Date(advancedFilters.importDateTo + ' 23:59:59')) {
          return false;
        }
      }

      // 聯絡方式篩選
      if (advancedFilters.hasPhone === true && !(card.mobile_phone || card.company_phone1 || card.company_phone2)) {
        return false;
      }
      if (advancedFilters.hasPhone === false && (card.mobile_phone || card.company_phone1 || card.company_phone2)) {
        return false;
      }

      if (advancedFilters.hasEmail === true && !card.email) {
        return false;
      }
      if (advancedFilters.hasEmail === false && card.email) {
        return false;
      }

      if (advancedFilters.hasAddress === true && !(card.company_address1_zh || card.company_address2_zh)) {
        return false;
      }
      if (advancedFilters.hasAddress === false && (card.company_address1_zh || card.company_address2_zh)) {
        return false;
      }

      return true;
    });
  };

  // 搜索功能和標籤篩選 - 使用服務器端搜索
  useEffect(() => {
    // 當搜索條件或標籤篩選改變時，重新載入第一頁
    const timeoutId = setTimeout(() => {
      loadCards(false);
    }, 300); // 防抖300ms

    return () => clearTimeout(timeoutId);
  }, [searchText, industryFilter]);

  // 客戶端篩選（狀態篩選和高級篩選）
  useEffect(() => {
    let filtered = cards;

    // 狀態篩選
    if (filterStatus !== 'all') {
      filtered = filtered.filter(card => {
        const cardStatus = checkCardStatus(card);
        return cardStatus.status === filterStatus;
      });
    }

    // 高級篩選
    filtered = applyAdvancedFilters(filtered);

    setFilteredCards(filtered);
  }, [cards, filterStatus, advancedFilters]);

  // 刪除名片
  const handleDeleteCard = async (cardId) => {
    Modal.confirm({
      content: '確定要刪除這張名片嗎？',
      onConfirm: async () => {
        try {
          await axios.delete(`/api/v1/cards/${cardId}`);
          Toast.show({
            content: '刪除成功',
            position: 'center',
          });
          loadCards(); // 重新載入列表
          loadGlobalStats(); // 更新全局統計
        } catch (error) {
          console.error('刪除失敗:', error);
          Toast.show({
            content: '刪除失敗',
            position: 'center',
          });
        }
      },
    });
  };

  // 刪除所有名片
  const handleDeleteAllCards = async () => {
    if (cards.length === 0) {
      Toast.show({
        content: '沒有名片可以刪除',
        position: 'center',
      });
      return;
    }

    Modal.confirm({
      content: `確定要刪除所有 ${cards.length} 張名片嗎？此操作無法撤銷！`,
      onConfirm: async () => {
        try {
          await axios.delete('/api/v1/cards/all');
          Toast.show({
            content: '所有名片已刪除',
            position: 'center',
          });
          loadCards(); // 重新載入列表
          loadGlobalStats(); // 更新全局統計
        } catch (error) {
          console.error('刪除所有名片失敗:', error);
          Toast.show({
            content: '刪除失敗',
            position: 'center',
          });
        }
      },
    });
  };

  // 匯出名片
  const handleExport = async (format) => {
    try {
      const response = await axios.get(`/api/v1/cards/export/download?format=${format}`, {
        responseType: 'blob',
      });
      
      // 創建下載鏈接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const fileExtension = format === 'excel' ? 'xlsx' : (format === 'vcard' ? 'vcf' : 'csv');
      link.setAttribute('download', `cards.${fileExtension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      Toast.show({
        content: `${format.toUpperCase()}匯出成功`,
        position: 'center',
      });
    } catch (error) {
      console.error('匯出失敗:', error);
      Toast.show({
        content: '匯出失敗',
        position: 'center',
      });
    }
  };

  // 處理文件選擇
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // 檢查文件格式
      const allowedTypes = [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv'
      ];
      const allowedExtensions = ['.xlsx', '.xls', '.csv'];
      
      const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
      
      // 檢查文件大小（50MB限制）
      const maxSizeMB = 50;
      const fileSizeMB = file.size / (1024 * 1024);
      
      if (fileSizeMB > maxSizeMB) {
        Toast.show({
          content: `文件過大（${fileSizeMB.toFixed(1)}MB），請使用小於 ${maxSizeMB}MB 的文件`,
          position: 'center',
        });
        return;
      }
      
      if (allowedTypes.includes(file.type) || allowedExtensions.includes(fileExtension)) {
        setUploadFile(file);
        setUploadModalVisible(true);
      } else {
        Toast.show({
          content: '請選擇 Excel (.xlsx, .xls) 或 CSV (.csv) 文件',
          position: 'center',
        });
      }
    }
    // 清空input值，允許重複選擇同一個文件
    event.target.value = '';
  };

  // 執行文本導入
  const handleTextImport = async () => {
    if (!uploadFile) {
      Toast.show({
        content: '請先選擇文件',
        position: 'center',
      });
      return;
    }

    setUploadLoading(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);

      // 模擬進度更新
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 500);

      const response = await axios.post('/api/v1/cards/text-import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted * 0.5); // 上傳佔50%
        },
      });
      
      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.data && response.data.success) {
        const stats = response.data.data;
        
        // 構建簡化的統計信息顯示
        let simpleMessage = `✅ 導入完成！成功 ${stats.final_success_count} 張`;
        
        const extras = [];
        if (stats.db_duplicate_count > 0) {
          extras.push(`重複 ${stats.db_duplicate_count}`);
        }
        if (stats.db_problem_count > 0) {
          extras.push(`問題 ${stats.db_problem_count}`);
        }
        if (stats.db_error_count > 0) {
          extras.push(`失敗 ${stats.db_error_count}`);
        }
        
        if (extras.length > 0) {
          simpleMessage += `，${extras.join('，')} 張`;
        }
        
        console.log('文本導入統計詳情:', stats);
        
        Toast.show({
          content: simpleMessage,
          position: 'center',
          duration: 3000,
        });
        
        setUploadModalVisible(false);
        setUploadFile(null);
        loadCards(); // 重新載入名片列表
        loadGlobalStats(); // 更新全局統計
      } else {
        Toast.show({
          content: response.data?.message || '導入失敗',
          position: 'center',
        });
      }
    } catch (error) {
      console.error('文本導入失敗:', error);
      Toast.show({
        content: error.response?.data?.message || '導入失敗',
        position: 'center',
      });
    } finally {
      setUploadLoading(false);
      setUploadProgress(0);
    }
  };

  // 渲染名片項目
  const renderCardItem = (card) => {
    const cardStatus = checkCardStatus(card);
    const cardStyle = {
      marginBottom: '12px',
      cursor: 'pointer',
      border: cardStatus.status === 'problem' ? '2px solid #ff7875' : '1px solid #d9d9d9',
      backgroundColor: cardStatus.status === 'problem' ? '#fff2f0' : '#ffffff'
    };

    // 獲取圖片URL
    const frontImageUrl = getImageUrl(card.front_image_path);
    const backImageUrl = getImageUrl(card.back_image_path);
    const hasImage = frontImageUrl || backImageUrl;

    return (
    <Card
      key={card.id}
      style={cardStyle}
      bodyStyle={{ padding: '16px' }}
      onClick={() => navigate(`/cards/${card.id}`)}
    >
      <div className="card-content">
        {/* 名片圖片預覽 */}
        {hasImage && (
          <div style={{
            display: 'flex',
            gap: '8px',
            marginBottom: '12px',
            padding: '8px',
            backgroundColor: '#f5f5f5',
            borderRadius: '6px',
            maxWidth: '280px'
          }}>
            {frontImageUrl && (
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '11px', color: '#999', marginBottom: '4px' }}>正面</div>
                <Image
                  src={frontImageUrl}
                  fit="cover"
                  style={{
                    width: '100%',
                    height: '70px',
                    borderRadius: '4px',
                    objectFit: 'cover',
                    cursor: 'pointer'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    ImageViewer.show({ image: frontImageUrl });
                  }}
                  fallback={
                    <div style={{
                      width: '100%',
                      height: '80px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: '#f0f0f0',
                      borderRadius: '4px',
                      color: '#999'
                    }}>
                      <PictureOutline fontSize={24} />
                    </div>
                  }
                />
              </div>
            )}
            {backImageUrl && (
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '11px', color: '#999', marginBottom: '4px' }}>反面</div>
                <Image
                  src={backImageUrl}
                  fit="cover"
                  style={{
                    width: '100%',
                    height: '70px',
                    borderRadius: '4px',
                    objectFit: 'cover',
                    cursor: 'pointer'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    ImageViewer.show({ image: backImageUrl });
                  }}
                  fallback={
                    <div style={{
                      width: '100%',
                      height: '80px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: '#f0f0f0',
                      borderRadius: '4px',
                      color: '#999'
                    }}>
                      <PictureOutline fontSize={24} />
                    </div>
                  }
                />
              </div>
            )}
          </div>
        )}
        {/* 狀態標記 */}
        {cardStatus.status === 'problem' && (
          <div style={{ 
            marginBottom: '12px', 
            padding: '12px', 
            backgroundColor: '#fff2f0', 
            border: '1px solid #ffccc7',
            borderRadius: '6px',
            borderLeft: '4px solid #ff4d4f'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#cf1322' }}>
                  ⚠️ 資料不完整
                </span>
                <Tag color="error" size="small">
                  缺少 {cardStatus.missingCount} 項
                </Tag>
              </div>
              <Button 
                size="small" 
                color="primary" 
                fill="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/cards/${card.id}`);
                }}
              >
                立即修復
              </Button>
            </div>
            
            <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '6px' }}>
              缺少以下重要信息：
            </div>
            
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
              {cardStatus.missingFields.map((field, index) => (
                <span 
                  key={index}
                  style={{ 
                    fontSize: '11px', 
                    padding: '2px 6px', 
                    backgroundColor: '#ffa39e', 
                    color: '#ffffff',
                    borderRadius: '3px',
                    fontWeight: '500'
                  }}
                >
                  {field}
                </span>
              ))}
            </div>
            
            <div style={{ fontSize: '11px', color: '#666666', lineHeight: '1.4' }}>
              💡 建議：點擊「立即修復」編輯名片，或通過OCR重新掃描補充缺失信息
            </div>
          </div>
        )}

        {/* 基本資訊 */}
        <div className="card-header" style={{ marginBottom: '12px' }}>
          <div className="name-company" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserContactOutline style={{ color: '#1890ff' }} />
            <div>
              <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#262626' }}>
                <HighlightText text={card.name_zh || '未知姓名'} keyword={searchText} />
                {card.name_en && (
                  <span style={{ fontSize: '14px', color: '#666', marginLeft: '8px' }}>
                    (<HighlightText text={card.name_en} keyword={searchText} />)
                  </span>
                )}
              </div>
              {card.company_name_zh && (
                <div style={{ fontSize: '14px', color: '#8c8c8c' }}>
                  <HighlightText text={card.company_name_zh} keyword={searchText} />
                  {card.company_name_en && (
                    <span style={{ fontSize: '12px', color: '#999', marginLeft: '6px' }}>
                      (<HighlightText text={card.company_name_en} keyword={searchText} />)
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
          <div style={{ marginTop: '4px' }}>
            {card.position_zh && (
              <Tag color="blue" style={{ marginRight: '4px' }}>
                職位1: <HighlightText text={card.position_zh} keyword={searchText} />
              </Tag>
            )}
            {card.position1_zh && (
              <Tag color="blue">
                職位2: <HighlightText text={card.position1_zh} keyword={searchText} />
              </Tag>
            )}
          </div>
          {/* 产业分类标签 */}
          {card.industry_category && (
            <div style={{ marginTop: '8px' }}>
              <Tag
                color={
                  card.industry_category === '防詐' ? 'warning' :
                  card.industry_category === '旅宿' ? 'success' :
                  card.industry_category === '工業應用' ? 'primary' :
                  card.industry_category === '食品業' ? 'default' :
                  'default'
                }
                style={{ fontSize: '12px' }}
              >
                🏢 {card.industry_category}
                {card.classification_confidence &&
                  ` (${Math.round(card.classification_confidence)}%)`
                }
              </Tag>
            </div>
          )}
          {(card.department1_zh || card.department2_zh || card.department3_zh) && (
            <div style={{ marginTop: '4px', fontSize: '13px', color: '#666' }}>
              <HighlightText
                text={[card.department1_zh, card.department2_zh, card.department3_zh]
                  .filter(Boolean)
                  .join(' / ')}
                keyword={searchText}
              />
            </div>
          )}
        </div>

        {/* 聯絡資訊 */}
        <div className="contact-info" style={{ marginBottom: '12px' }}>
          {card.mobile_phone && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <PhoneFill style={{ color: '#52c41a', fontSize: '14px' }} />
              <span style={{ fontSize: '14px' }}>
                <HighlightText text={card.mobile_phone} keyword={searchText} />
              </span>
            </div>
          )}
          {card.company_phone1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <PhoneFill style={{ color: '#1890ff', fontSize: '14px' }} />
              <span style={{ fontSize: '14px' }}>
                <HighlightText text={card.company_phone1} keyword={searchText} />
              </span>
            </div>
          )}
          {card.company_phone2 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <PhoneFill style={{ color: '#1890ff', fontSize: '14px' }} />
              <span style={{ fontSize: '14px' }}>
                <HighlightText text={card.company_phone2} keyword={searchText} />
              </span>
            </div>
          )}
          {card.email && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <MailOutline style={{ color: '#fa8c16', fontSize: '14px' }} />
              <span style={{ fontSize: '14px' }}>
                <HighlightText text={card.email} keyword={searchText} />
              </span>
            </div>
          )}
          {(card.company_address1_zh || card.company_address2_zh) && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
              <EnvironmentOutline style={{ color: '#eb2f96', fontSize: '14px', marginTop: '2px' }} />
              <div style={{ fontSize: '14px', lineHeight: '1.4' }}>
                <HighlightText text={card.company_address1_zh} keyword={searchText} />
                {card.company_address2_zh && (
                  <div><HighlightText text={card.company_address2_zh} keyword={searchText} /></div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 其他資訊 */}
        {(card.line_id || card.note1 || card.note2) && (
          <div className="extra-info" style={{ marginBottom: '12px' }}>
            {card.line_id && (
              <div style={{ fontSize: '14px', color: '#8c8c8c', marginBottom: '4px' }}>
                Line ID: {card.line_id}
              </div>
            )}
            {card.note1 && (
              <div style={{ fontSize: '14px', color: '#8c8c8c', marginBottom: '4px' }}>
                note1: {card.note1}
              </div>
            )}
            {card.note2 && (
              <div style={{ fontSize: '14px', color: '#8c8c8c' }}>
                note2: {card.note2}
              </div>
            )}
          </div>
        )}

        {/* 操作按鈕 */}
        <div className="card-actions" style={{ borderTop: '1px solid #f0f0f0', paddingTop: '12px' }}>
          <Space>
            <Button 
              size="small" 
              color="primary" 
              fill="outline"
              onClick={(e) => {
                e.stopPropagation(); // 防止觸發卡片點擊事件
                navigate(`/cards/${card.id}`);
              }}
            >
              <EditSOutline /> 編輯
            </Button>
            <Button 
              size="small" 
              color="danger" 
              fill="outline"
              onClick={(e) => {
                e.stopPropagation(); // 防止觸發卡片點擊事件
                handleDeleteCard(card.id);
              }}
            >
              <DeleteOutline /> 刪除
            </Button>
          </Space>
        </div>
      </div>
    </Card>
    );
  };

  return (
    <div className="card-manager-page">
      <NavBar onBack={() => navigate('/')}>名片管理</NavBar>
      
      <div className="content" style={{ padding: '16px' }}>
        {/* 搜索欄 */}
        <SearchBar
          placeholder="搜索名片（姓名、公司、職稱、電話、郵箱）支援中英文"
          value={searchText}
          onChange={setSearchText}
          style={{ marginBottom: '16px' }}
        />

        {/* 產業篩選和批量分類 */}
        <Card style={{ marginBottom: '16px' }}>
          <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '14px', fontWeight: 'bold' }}>產業篩選</span>
            <Button
              color="primary"
              size="small"
              onClick={handleBatchClassify}
              loading={classifying}
            >
              🤖 批量AI分类
            </Button>
          </div>
          <Selector
            options={[
              { label: '全部產業', value: '全部' },
              { label: '防詐', value: '防詐' },
              { label: '旅宿', value: '旅宿' },
              { label: '工業應用', value: '工業應用' },
              { label: '食品業', value: '食品業' },
              { label: '其他', value: '其他' },
            ]}
            value={[industryFilter]}
            onChange={(arr) => setIndustryFilter(arr[0] || '全部')}
            style={{ '--border-radius': '8px' }}
          />
        </Card>

        {/* 篩選按鈕 */}
        <Card style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '14px', fontWeight: 'bold' }}>篩選條件</span>
            <Button 
              size="small" 
              color="primary" 
              fill="outline"
              onClick={() => setAdvancedFilterVisible(!advancedFilterVisible)}
            >
              高級篩選 {advancedFilterVisible ? '收起' : '展開'}
            </Button>
          </div>
          
          <Space>
            <Button 
              color={filterStatus === 'all' ? 'primary' : 'default'}
              fill={filterStatus === 'all' ? 'solid' : 'outline'}
              size="small"
              onClick={() => setFilterStatus('all')}
            >
              全部 ({globalStats.total})
            </Button>
            <Button 
              color={filterStatus === 'normal' ? 'success' : 'default'}
              fill={filterStatus === 'normal' ? 'solid' : 'outline'}
              size="small"
              onClick={() => setFilterStatus('normal')}
            >
              正常 ({globalStats.normal})
            </Button>
            <Button 
              color={filterStatus === 'problem' ? 'danger' : 'default'}
              fill={filterStatus === 'problem' ? 'solid' : 'outline'}
              size="small"
              onClick={() => setFilterStatus('problem')}
            >
              有問題 ({globalStats.problem})
            </Button>
          </Space>

          {/* 高級篩選面板 */}
          {advancedFilterVisible && (
            <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
              <div style={{ marginBottom: '12px', fontSize: '14px', fontWeight: 'bold' }}>高級篩選選項</div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <div style={{ marginBottom: '4px', fontSize: '13px' }}>中文姓名</div>
                  <input
                    type="text"
                    placeholder="輸入中文姓名"
                    value={advancedFilters.name_zh}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, name_zh: e.target.value }))}
                    style={{ 
                      width: '100%', 
                      padding: '8px', 
                      border: '1px solid #d9d9d9', 
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  />
                </div>
                
                <div>
                  <div style={{ marginBottom: '4px', fontSize: '13px' }}>英文姓名</div>
                  <input
                    type="text"
                    placeholder="輸入英文姓名"
                    value={advancedFilters.name_en}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, name_en: e.target.value }))}
                    style={{ 
                      width: '100%', 
                      padding: '8px', 
                      border: '1px solid #d9d9d9', 
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <div style={{ marginBottom: '4px', fontSize: '13px' }}>公司名稱</div>
                  <input
                    type="text"
                    placeholder="輸入公司名稱"
                    value={advancedFilters.company}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, company: e.target.value }))}
                    style={{ 
                      width: '100%', 
                      padding: '8px', 
                      border: '1px solid #d9d9d9', 
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  />
                </div>
                
                <div>
                  <div style={{ marginBottom: '4px', fontSize: '13px' }}>職位</div>
                  <input
                    type="text"
                    placeholder="輸入職位"
                    value={advancedFilters.position}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, position: e.target.value }))}
                    style={{ 
                      width: '100%', 
                      padding: '8px', 
                      border: '1px solid #d9d9d9', 
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <div style={{ marginBottom: '4px', fontSize: '13px' }}>導入日期範圍</div>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <input
                      type="date"
                      value={advancedFilters.importDateFrom}
                      onChange={(e) => setAdvancedFilters(prev => ({ ...prev, importDateFrom: e.target.value }))}
                      style={{ 
                        flex: 1,
                        padding: '8px', 
                        border: '1px solid #d9d9d9', 
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}
                    />
                    <input
                      type="date"
                      value={advancedFilters.importDateTo}
                      onChange={(e) => setAdvancedFilters(prev => ({ ...prev, importDateTo: e.target.value }))}
                      style={{ 
                        flex: 1,
                        padding: '8px', 
                        border: '1px solid #d9d9d9', 
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}
                    />
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <div style={{ marginBottom: '8px', fontSize: '13px' }}>聯絡方式篩選</div>
                <Space>
                  <Button 
                    size="small" 
                    color={advancedFilters.hasPhone === true ? 'primary' : 'default'}
                    fill={advancedFilters.hasPhone === true ? 'solid' : 'outline'}
                    onClick={() => setAdvancedFilters(prev => ({ 
                      ...prev, 
                      hasPhone: prev.hasPhone === true ? null : true 
                    }))}
                  >
                    有電話
                  </Button>
                  <Button 
                    size="small" 
                    color={advancedFilters.hasEmail === true ? 'primary' : 'default'}
                    fill={advancedFilters.hasEmail === true ? 'solid' : 'outline'}
                    onClick={() => setAdvancedFilters(prev => ({ 
                      ...prev, 
                      hasEmail: prev.hasEmail === true ? null : true 
                    }))}
                  >
                    有郵箱
                  </Button>
                  <Button 
                    size="small" 
                    color={advancedFilters.hasAddress === true ? 'primary' : 'default'}
                    fill={advancedFilters.hasAddress === true ? 'solid' : 'outline'}
                    onClick={() => setAdvancedFilters(prev => ({ 
                      ...prev, 
                      hasAddress: prev.hasAddress === true ? null : true 
                    }))}
                  >
                    有地址
                  </Button>
                </Space>
              </div>

              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <Button 
                  size="small" 
                  onClick={() => setAdvancedFilters({
                    company: '',
                    position: '',
                    name_zh: '',
                    name_en: '',
                    importDateFrom: '',
                    importDateTo: '',
                    hasPhone: null,
                    hasEmail: null,
                    hasAddress: null
                  })}
                >
                  清空篩選
                </Button>
                <Button 
                  size="small" 
                  color="primary"
                  onClick={() => setAdvancedFilterVisible(false)}
                >
                  確定
                </Button>
              </div>
            </div>
          )}
        </Card>

        {/* 操作按鈕 */}
        <Card style={{ marginBottom: '16px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space style={{ width: '100%', gap: '8px' }}>
              <Button 
                color="primary" 
                size="large" 
                style={{ flex: 1 }}
                onClick={() => navigate('/add-card')}
              >
                <AddOutline /> 手動新增
              </Button>
              <Button 
                color="warning" 
                size="large" 
                style={{ flex: 1 }}
                onClick={() => navigate('/scan')}
              >
                <AddOutline /> OCR掃描
              </Button>
              <Button 
                color="success" 
                size="large" 
                style={{ flex: 1 }}
                onClick={() => document.getElementById('file-input').click()}
              >
                <UploadOutline /> 文本導入
              </Button>
            </Space>
            
            {/* 隱藏的文件選擇器 */}
            <input
              id="file-input"
              type="file"
              accept=".xlsx,.xls,.csv"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />
            
            <Divider>匯出功能</Divider>
            
            <Space style={{ width: '100%' }}>
              <Button 
                color="default" 
                fill="outline"
                style={{ flex: 1 }}
                onClick={() => handleExport('csv')}
              >
                <DownlandOutline /> CSV
              </Button>
              <Button 
                color="default" 
                fill="outline"
                style={{ flex: 1 }}
                onClick={() => handleExport('excel')}
              >
                <DownlandOutline /> Excel
              </Button>
            </Space>
            
            {/* 統計信息 */}
            <div style={{ 
              marginTop: '16px', 
              padding: '12px 16px', 
              backgroundColor: '#f8f9fa', 
              borderRadius: '8px',
              border: '1px solid #e9ecef',
              display: 'none'  // 隱藏統計信息
            }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '8px', color: '#495057' }}>
                名片統計
              </div>
              <div style={{ display: 'flex', gap: '24px', justifyContent: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#1890ff' }}>
                    {cards.length}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6c757d' }}>總計</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#52c41a' }}>
                    {cards.filter(card => checkCardStatus(card).status === 'normal').length}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6c757d' }}>正常</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#ff4d4f' }}>
                    {cards.filter(card => checkCardStatus(card).status === 'problem').length}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6c757d' }}>有問題</div>
                </div>
              </div>
            </div>
          </Space>
        </Card>

        {/* 名片列表 */}
        <div className="cards-list">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div>載入中...</div>
            </div>
          ) : filteredCards.length === 0 ? (
            <Empty
              style={{ padding: '40px' }}
              description={
                searchText || Object.values(advancedFilters).some(v => v) ? 
                  "沒有找到符合條件的名片" : 
                  "還沒有名片，點擊上方按鈕新增"
              }
            />
          ) : (
            <div>
              {(searchText || Object.values(advancedFilters).some(v => v) || filterStatus !== 'all' || industryFilter !== '全部') && (
                <div style={{
                  marginBottom: '12px',
                  padding: '8px',
                  backgroundColor: '#e6f7ff',
                  borderRadius: '4px',
                  fontSize: '13px',
                  color: '#0050b3',
                  border: '1px solid #91d5ff'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>
                      {searchText && `'${searchText}' `}
                      {industryFilter !== '全部' ? (
                        // 特定產業：如果有篩選條件則顯示篩選後數量，否則顯示總數
                        `📊 ${industryFilter}: ${
                          searchText || Object.values(advancedFilters).some(v => v) || filterStatus !== 'all'
                            ? filteredCards.length  // 有篩選條件：顯示篩選結果
                            : (globalStats.industry_stats?.[industryFilter] || 0)  // 無篩選：顯示總數
                        } 張`
                      ) : (
                        // 全部產業：顯示各產業統計
                        globalStats.industry_stats && Object.keys(globalStats.industry_stats).length > 0 ? (
                          `📊 ${Object.entries(globalStats.industry_stats)
                            .sort(([,a], [,b]) => b - a)
                            .map(([cat, count]) => `${cat}: ${count}`)
                            .join(' | ')}`
                        ) : '📊 載入中...'
                      )}
                    </span>
                    <span style={{ fontSize: '12px', color: '#999' }}>
                      {searchText && `關鍵詞: "${searchText}"`}
                      {industryFilter !== '全部' && (searchText ? ' | ' : '') + `產業: ${industryFilter}`}
                      {Object.values(advancedFilters).some(v => v) && " | 高級篩選"}
                      {filterStatus !== 'all' && ` | 狀態: ${filterStatus === 'normal' ? '正常' : '有問題'}`}
                    </span>
                  </div>
                </div>
              )}
              <div>
                {filteredCards.map(renderCardItem)}
                <InfiniteScroll 
                  loadMore={loadMore} 
                  hasMore={hasMore}
                  threshold={100}
                >
                  <div style={{ 
                    padding: '20px', 
                    textAlign: 'center',
                    color: '#999',
                    fontSize: '14px'
                  }}>
                    {hasMore ? (
                      <>
                        <DotLoading color='primary' />
                        <div style={{ marginTop: '8px' }}>加載中...</div>
                      </>
                    ) : (
                      <div>沒有更多數據了</div>
                    )}
                  </div>
                </InfiniteScroll>
              </div>
            </div>
          )}
        </div>

        {/* 文本導入確認對話框 */}
        <Modal
          visible={uploadModalVisible}
          title="文本導入確認"
          onClose={() => {
            setUploadModalVisible(false);
            setUploadFile(null);
          }}
          closeOnAction
          actions={[
            {
              key: 'cancel',
              text: '取消',
              onClick: () => {
                setUploadModalVisible(false);
                setUploadFile(null);
              }
            },
            {
              key: 'confirm',
              text: uploadLoading ? '導入中...' : '確認導入',
              color: 'primary',
              loading: uploadLoading,
              onClick: handleTextImport
            }
          ]}
        >
          <div style={{ padding: '16px 0' }}>
            {uploadFile && (
              <div>
                <p><strong>選擇的文件：</strong>{uploadFile.name}</p>
                <p><strong>文件大小：</strong>{(uploadFile.size / 1024 / 1024).toFixed(2)} MB</p>
                <p><strong>文件類型：</strong>{uploadFile.type || '未知'}</p>
                
                {uploadLoading && (
                  <div style={{ marginTop: '16px' }}>
                    <div style={{ marginBottom: '8px', fontSize: '14px', color: '#1890ff' }}>
                      正在導入中，請稍候...
                    </div>
                    <ProgressBar 
                      percent={uploadProgress} 
                      style={{ 
                        '--track-width': '8px',
                        '--fill-color': '#1890ff'
                      }}
                    />
                    <div style={{ marginTop: '4px', fontSize: '12px', color: '#999', textAlign: 'center' }}>
                      {uploadProgress < 50 ? '上傳文件中...' : 
                       uploadProgress < 90 ? '解析數據中...' : 
                       '保存數據中...'}
                    </div>
                  </div>
                )}
                
                <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f6f6f6', borderRadius: '6px' }}>
                  <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>
                    <strong>說明：</strong>系統將自動識別文件中的名片欄位並批量導入。
                    支援的欄位包括：姓名、公司名稱、職位、手機、電話、郵箱、地址等。
                  </p>
                  <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#999' }}>
                    📊 優化提示：系統使用批量插入技術，可快速處理大量數據。
                  </p>
                </div>
              </div>
            )}
          </div>
        </Modal>

        {/* 批量分类进度对话框 */}
        <Modal
          visible={progressVisible}
          content={
            <div style={{ padding: '20px' }}>
              <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>🤖 AI 批量分类进行中</h3>
                <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>
                  {taskProgress?.status === 'processing'
                    ? '正在使用AI分析名片產業類別...'
                    : taskProgress?.status === 'pending'
                    ? '任务准备中...'
                    : taskProgress?.status === 'completed'
                    ? '分类完成！'
                    : taskProgress?.status === 'failed'
                    ? '分类失败'
                    : '任务已取消'}
                </p>
              </div>

              {taskProgress && (
                <>
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '8px',
                      fontSize: '14px'
                    }}>
                      <span>进度：{taskProgress.completed} / {taskProgress.total}</span>
                      <span>{taskProgress.progress_percent?.toFixed(1)}%</span>
                    </div>
                    <ProgressBar
                      percent={taskProgress.progress_percent || 0}
                      style={{
                        '--fill-color': taskProgress.status === 'failed' ? '#ff4d4f' : '#1677ff',
                      }}
                    />
                  </div>

                  <div style={{
                    padding: '12px',
                    backgroundColor: '#f6f6f6',
                    borderRadius: '6px',
                    fontSize: '13px',
                    marginBottom: '16px'
                  }}>
                    <div style={{ marginBottom: '6px' }}>
                      <span style={{ color: '#666' }}>成功：</span>
                      <span style={{ color: '#52c41a', fontWeight: 'bold' }}>
                        {taskProgress.success_count || 0}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#666' }}>失败：</span>
                      <span style={{ color: '#ff4d4f', fontWeight: 'bold' }}>
                        {taskProgress.failed || 0}
                      </span>
                    </div>
                  </div>

                  {taskProgress.error_message && (
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#fff2e8',
                      border: '1px solid #ffbb96',
                      borderRadius: '6px',
                      fontSize: '13px',
                      color: '#d4380d'
                    }}>
                      ⚠️ {taskProgress.error_message}
                    </div>
                  )}

                  {taskProgress.status === 'processing' && (
                    <Button
                      block
                      color="danger"
                      onClick={handleCancelTask}
                      style={{ marginTop: '16px' }}
                    >
                      取消任务
                    </Button>
                  )}
                </>
              )}
            </div>
          }
          closeOnMaskClick={false}
          showCloseButton={taskProgress?.status !== 'processing'}
          onClose={() => {
            setProgressVisible(false);
            setTaskProgress(null);
            if (pollingInterval) {
              clearInterval(pollingInterval);
            }
          }}
        />
      </div>
    </div>
  );
};

export default CardManagerPage; 