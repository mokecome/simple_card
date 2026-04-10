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
  PictureOutline,
  StarOutline
} from 'antd-mobile-icons';
import { Image, ImageViewer } from 'antd-mobile';
import axios from 'axios';
import { Dialog } from 'antd-mobile';


const CardManagerPage = () => {
  const navigate = useNavigate(); 
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [filteredCards, setFilteredCards] = useState([]);

  // ⬇ 新增：目前這組「search + 產業 + 狀態」條件下，後端告訴你的總筆數
  const [filteredTotal, setFilteredTotal] = useState(0);
  // ⬇ 新增：本次條件（search + 全部產業 + status）下的各產業分布統計
  const [filteredIndustryStats, setFilteredIndustryStats] = useState({});

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

  // 12 大類固定顯示順序（後端原始分類名稱）
  const INDUSTRY_ORDER = [
    "資訊科技",
    "金融保險",
    "製造業／工業應用",
    "建築不動產",
    "交通運輸／物流",
    "醫療健康／生技",
    "餐飲／零售／通路",
    "廣告／媒體／行銷",
    "教育／學研",
    "政府／公部門／非營利",
    "專業服務（顧問／法務／會計等）",
    "不明／其他",
  ];

  // 後端分類名稱 → 前端顯示（你 Selector 的縮寫）
  const INDUSTRY_DISPLAY_NAME = {
    "資訊科技": "資訊科技",
    "金融保險": "金融保險",
    "製造業／工業應用": "製造業",
    "建築不動產": "建築不動產",
    "交通運輸／物流": "交通運輸",
    "醫療健康／生技": "醫療生技",
    "餐飲／零售／通路": "餐飲零售",
    "廣告／媒體／行銷": "行銷媒體",
    "教育／學研": "教育研究",
    "政府／公部門／非營利": "公部門組織",
    "專業服務（顧問／法務／會計等）": "專業服務",
    "不明／其他": "其他",
  };

  // 把 breakdown 依固定順序輸出 + 套用顯示名稱
  const formatIndustryBreakdown = (stats) => {
    if (!stats || Object.keys(stats).length === 0) return "";
    return INDUSTRY_ORDER
      .map((key) => {
        const count = stats[key];
        if (!count || count <= 0) return null; // 0 就不顯示
        const label = INDUSTRY_DISPLAY_NAME[key] || key;
        return `${label}：${count} 張`;
      })
      .filter(Boolean)
      .join("； ");
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
      const params = {
          use_pagination: true,
          skip: currentPageToLoad * pageSize,
          limit: pageSize,
          search: searchText || undefined,
          industry: industryFilter && industryFilter !== '全部' ? industryFilter : undefined,
          status: filterStatus !== 'all' ? filterStatus : undefined,
          // 高級篩選
          name_zh: advancedFilters.name_zh || undefined,
          name_en: advancedFilters.name_en || undefined,
          company: advancedFilters.company || undefined,
          position: advancedFilters.position || undefined,
          date_from: advancedFilters.importDateFrom || undefined,
          date_to: advancedFilters.importDateTo || undefined,
          has_phone: advancedFilters.hasPhone !== null ? advancedFilters.hasPhone : undefined,
          has_email: advancedFilters.hasEmail !== null ? advancedFilters.hasEmail : undefined,
          has_address: advancedFilters.hasAddress !== null ? advancedFilters.hasAddress : undefined,
      };
      const response = await axios.get('/api/v1/cards/', { params });
      
      if (response.data && response.data.success && response.data.data) {
        const { items, total, has_more, industry_stats, industry_breakdown } = response.data.data;

        // ⬇ 新增：更新本次條件下的產業分布
        setFilteredIndustryStats(industry_stats || industry_breakdown || {});

        // ⬇ 新增：不管是不是載更多，都更新「符合條件的總筆數」
        setFilteredTotal(total || 0);
        
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


  // 所有篩選條件改變時，重新從後端載入（防抖 300ms）
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadCards(false);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchText, industryFilter, filterStatus, advancedFilters]);

  // 刪除名片
  const handleDeleteCard = async (cardId) => {
    const confirmed = await Dialog.confirm({
      content: '確定要刪除這張名片嗎？',
      confirmText: '確定',
      cancelText: '取消',
    })
    if (!confirmed) return
    try {
      await axios.delete(`/api/v1/cards/${cardId}`)
      Toast.show({ content: '名片已刪除', position: 'center' })
      loadCards()
      loadGlobalStats?.()
    } 
    catch (error) {
        Toast.show({ content: '刪除失敗', position: 'center' })
    }
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

  // 匯出名片（帶篩選條件，含高級篩選）
  const handleExport = async (format) => {
    try {
      const params = new URLSearchParams({ format });
      if (searchText) params.append('search', searchText);
      if (industryFilter && industryFilter !== '全部') params.append('industry', industryFilter);
      if (filterStatus && filterStatus !== 'all') params.append('status', filterStatus);
      // 高級篩選
      if (advancedFilters.name_zh) params.append('name_zh', advancedFilters.name_zh);
      if (advancedFilters.name_en) params.append('name_en', advancedFilters.name_en);
      if (advancedFilters.company) params.append('company', advancedFilters.company);
      if (advancedFilters.position) params.append('position', advancedFilters.position);
      if (advancedFilters.importDateFrom) params.append('date_from', advancedFilters.importDateFrom);
      if (advancedFilters.importDateTo) params.append('date_to', advancedFilters.importDateTo);
      if (advancedFilters.hasPhone !== null) params.append('has_phone', advancedFilters.hasPhone);
      if (advancedFilters.hasEmail !== null) params.append('has_email', advancedFilters.hasEmail);
      if (advancedFilters.hasAddress !== null) params.append('has_address', advancedFilters.hasAddress);

      const response = await axios.get(`/api/v1/cards/export/download?${params.toString()}`, {
        responseType: 'blob',
      });

      // 從 Content-Disposition 取得檔名
      const disposition = response.headers['content-disposition'];
      let filename = `cards.${format === 'excel' ? 'xlsx' : format === 'vcard' ? 'vcf' : 'csv'}`;
      if (disposition) {
        const match = disposition.match(/filename=(.+)/);
        if (match) filename = match[1];
      }

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
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
      //const allowedExtensions = ['.xlsx', '.xls', '.csv'];
      const allowedExtensions = ['.wcxf'];
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
          //content: '請選擇 Excel (.xlsx, .xls) 或 CSV (.csv) 文件',
          content: '請選擇名片王匯出的 .wcxf 檔案',
          position: 'center',
        });
      }
    }
    // 清空input值，允許重複選擇同一個文件
    event.target.value = '';
  };

  /*
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
  */

  // 執行名片王匯入（WCXF）
  const handleTextImport = async () => {
    if (!uploadFile) {
      Toast.show({
        content: '請先選擇檔案（.wcxf）',
        position: 'center',
      });
      return;
    }

    setUploadLoading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', uploadFile);

      // 模擬進度更新（保留你原本的體驗）
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 500);

      const response = await axios.post('/api/v1/cards/wcxf-import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (!progressEvent.total) return;
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          // 上傳階段佔 50%
          setUploadProgress(percentCompleted * 0.5);
        },
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.data && response.data.success) {
        const stats = response.data.data || {};
        const total = stats.total ?? 0;
        const imported = stats.imported ?? 0;
        const failed = stats.failed ?? 0;

        let simpleMessage = `✅ 名片王匯入完成！成功 ${imported} / ${total} 張`;
        if (failed > 0) {
          simpleMessage += `，失敗 ${failed} 張`;
        }

        console.log('名片王匯入統計詳情:', stats);

        Toast.show({
          content: simpleMessage,
          position: 'center',
          duration: 3000,
        });

        // 關閉上傳視窗 & 清空檔案
        setUploadModalVisible(false);
        setUploadFile(null);

        // 重新載入列表與全局統計
        loadCards();
        loadGlobalStats();
      } else {
        Toast.show({
          content: response.data?.message || '名片王匯入失敗',
          position: 'center',
        });
      }
    } catch (error) {
      console.error('名片王匯入失敗:', error);
      Toast.show({
        content: error.response?.data?.message || '名片王匯入失敗',
        position: 'center',
      });
    } finally {
      setUploadLoading(false);
      setUploadProgress(0);
    }
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
    const frontImageUrl = getImageUrl(card.front_cropped_image_path || card.front_image_path);
    const backImageUrl = getImageUrl(card.back_cropped_image_path || card.back_image_path);
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
              <div style={{ flex: 1, maxWidth: '50%' }}>
                <div style={{ fontSize: '11px', color: '#999', marginBottom: '4px' }}>正面</div>
                <Image
                  src={frontImageUrl}
                  fit="contain"
                  style={{
                    width: '100%',
                    height: '70px',
                    borderRadius: '4px',
                    objectFit: 'contain',
                    backgroundColor: '#e8e8e8',
                    cursor: 'pointer'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    openImageViewer(frontImageUrl);
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
              <div style={{ flex: 1, maxWidth: '50%' }}>
                <div style={{ fontSize: '11px', color: '#999', marginBottom: '4px' }}>反面</div>
                <Image
                  src={backImageUrl}
                  fit="contain"
                  style={{
                    width: '100%',
                    height: '70px',
                    borderRadius: '4px',
                    objectFit: 'contain',
                    backgroundColor: '#e8e8e8',
                    cursor: 'pointer'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    openImageViewer(backImageUrl);
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
          {/* 產業分類標籤 */}
          {card.industry_category && (
            <div style={{ marginTop: '8px' }}>
              <Tag
                color={
                  card.industry_category === '資訊科技' ? 'primary' :
                  card.industry_category === '金融保險' ? 'warning' :
                  card.industry_category === '製造業／工業應用' ? 'success' :
                  card.industry_category === '建築不動產' ? 'default' :
                  card.industry_category === '交通運輸／物流' ? 'primary' :
                  card.industry_category === '醫療健康／生技' ? 'success' :
                  card.industry_category === '餐飲／零售／通路' ? 'warning' :
                  card.industry_category === '廣告／媒體／行銷' ? 'primary' :
                  card.industry_category === '教育／學研' ? 'default' :
                  card.industry_category === '政府／公部門／非營利' ? 'success' :
                  card.industry_category === '專業服務（顧問／法務／會計等）' ? 'warning' :
                  card.industry_category === '不明／其他' ? 'default' :
                  'default'
                }
                style={{ fontSize: '12px' }}
              >
                🏢 {card.industry_category}
                {typeof card.classification_confidence === 'number' &&
                  ` (${Math.round(card.classification_confidence * 100)}%)`
                }
              </Tag>
            </div>
          )}
          {card.duplicate_group_id && (
            <div style={{ marginTop: '4px' }}>
              <Tag
                color="danger"
                style={{ fontSize: '12px', cursor: 'pointer' }}
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/cards/duplicates/${card.duplicate_group_id}`);
                }}
              >
                重複 x{card.duplicate_count || '?'}
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
                navigate(`/cards/${card.id}?edit=true`);
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
              <StarOutline style={{ marginRight: '4px' }} />
              批量AI分類
            </Button>
          </div>
          <Selector
            options={[
              { label: '全部產業', value: '全部' },

              // 1. 資訊相關
              { label: '資訊科技', value: '資訊科技' },

              // 2. 金融相關
              { label: '金融保險', value: '金融保險' },

              // 3. 製造業／工業應用
              { label: '製造業', value: '製造業／工業應用' },

              // 4. 建築不動產
              { label: '建築不動產', value: '建築不動產' },

              // 5. 交通運輸／物流
              { label: '交通運輸', value: '交通運輸／物流' },

              // 6. 醫療健康／生技
              { label: '醫療生技', value: '醫療健康／生技' },

              // 7. 餐飲／零售／通路
              { label: '餐飲零售', value: '餐飲／零售／通路' },

              // 8. 廣告／媒體／行銷
              { label: '行銷媒體', value: '廣告／媒體／行銷' },

              // 9. 教育／學研
              { label: '教育研究', value: '教育／學研' },

              // 10. 政府／公部門／非營利
              { label: '公部門組織', value: '政府／公部門／非營利' },

              // 11. 專業服務
              { label: '專業服務', value: '專業服務（顧問／法務／會計等）' },

              // 12. 不明 / 其他
              { label: '其他', value: '不明／其他' },
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
            <Button
              color={filterStatus === 'duplicate' ? 'warning' : 'default'}
              fill={filterStatus === 'duplicate' ? 'solid' : 'outline'}
              size="small"
              onClick={() => setFilterStatus('duplicate')}
            >
              重複
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
            <div style={{ display: 'flex', gap: '8px', width: '100%', maxWidth: '480px' }}>
              <Button
                color="primary"
                size="middle"
                style={{ flex: 1, maxWidth: '160px', fontSize: '13px', padding: '8px 0' }}
                onClick={() => navigate('/add-card')}
              >
                <AddOutline /> 手動新增
              </Button>
              <Button
                color="warning"
                size="middle"
                style={{ flex: 1, maxWidth: '160px', fontSize: '13px', padding: '8px 0' }}
                onClick={() => navigate('/scan')}
              >
                <AddOutline /> OCR掃描
              </Button>
              <Button
                color="success"
                size="middle"
                style={{ flex: 1, maxWidth: '160px', fontSize: '13px', padding: '8px 0' }}
                onClick={() => document.getElementById('file-input').click()}
              >
                <UploadOutline /> 名片王匯入
              </Button>
            </div>
            
            {/* 隱藏的文件選擇器 */}
            <input
              id="file-input"
              type="file"
              accept=".wcxf"
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
                        `📊 ${industryFilter}: ${
                          (searchText || filterStatus !== 'all' || Object.values(advancedFilters).some(v => v !== '' && v !== null))
                            ? filteredTotal
                            : (globalStats.industry_stats?.[industryFilter] || 0)
                        } 張`
                      ) : (
                        // ✅ 全部產業：如果有 search / status 篩選 → 顯示總數；否則顯示各產業統計
                        (Object.values(advancedFilters).some(v => v) || searchText || filterStatus !== 'all') ? (
                          (() => {
                            const totalText = `📊 全部產業：${filteredTotal} 張`;

                            const breakdown = formatIndustryBreakdown(filteredIndustryStats);

                            return breakdown ? `${totalText}； ${breakdown}` : totalText;
                          })()
                        ) : (
                          globalStats.industry_stats && Object.keys(globalStats.industry_stats).length > 0 ? (
                            `📊 ${Object.entries(globalStats.industry_stats)
                              .sort(([,a], [,b]) => b - a)
                              .map(([cat, count]) => `${cat}: ${count}`)
                              .join(' | ')}`
                          ) : '📊 載入中...'
                        )
                      )}
                    </span>
                    <span style={{ fontSize: '12px', color: '#999' }}>
                      {searchText && `關鍵詞: "${searchText}"`}
                      {industryFilter !== '全部' && (searchText ? ' | ' : '') + `產業: ${industryFilter}`}
                      {Object.values(advancedFilters).some(v => v) && " | 高級篩選"}
                      {filterStatus !== 'all' && ` | 狀態: ${filterStatus === 'normal' ? '正常' : filterStatus === 'duplicate' ? '重複' : '有問題'}`}
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
          title="名片王匯入確認"
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
                <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <StarOutline style={{ fontSize: '20px' }} />
                  AI 批量分類進行中
                </h3>
                <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>
                  {taskProgress?.status === 'processing'
                    ? '正在使用AI分析名片產業類別...'
                    : taskProgress?.status === 'pending'
                    ? '任務準備中...'
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