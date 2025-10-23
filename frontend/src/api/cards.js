import axios from 'axios';
import { handleApiError } from '../utils/errorHandler';

// 讀取環境變數，支援多環境部署
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api/v1';

// 創建axios實例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 增加超時時間
  headers: {
    'Content-Type': 'application/json',
  },
});

// 請求攔截器
api.interceptors.request.use(
  (config) => {
    // 添加請求追蹤ID
    config.headers['X-Request-ID'] = generateRequestId();
    
    // 記錄請求日誌（開發環境）
    if (process.env.NODE_ENV === 'development') {
      console.log(`🚀 API請求: ${config.method?.toUpperCase()} ${config.url}`, {
        data: config.data,
        params: config.params
      });
    }
    
    return config;
  },
  (error) => {
    console.error('請求配置錯誤:', error);
    return Promise.reject(error);
  }
);

// 響應攔截器
api.interceptors.response.use(
  (response) => {
    // 記錄成功響應（開發環境）
    if (process.env.NODE_ENV === 'development') {
      console.log(`✅ API響應: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        status: response.status,
        data: response.data,
        traceId: response.headers['x-trace-id']
      });
    }
    
    return response;
  },
  (error) => {
    // 不在這裡處理錯誤，而是讓各個API調用處理
    // 但可以在這裡記錄通用的錯誤信息
    if (process.env.NODE_ENV === 'development') {
      console.error(`❌ API錯誤: ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        status: error.response?.status,
        data: error.response?.data,
        traceId: error.response?.headers['x-trace-id']
      });
    }
    
    return Promise.reject(error);
  }
);

// 生成請求ID
function generateRequestId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// 名片相關API
export const getCards = () => api.get('/cards/');

export const getCard = (id) => api.get(`/cards/${id}`);

export const createCard = (cardData) => {
  if (cardData instanceof FormData) {
    return api.post('/cards/', cardData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }
  return api.post('/cards/', cardData);
};

export const updateCard = (id, cardData) => api.put(`/cards/${id}`, cardData);

export const deleteCard = (id) => api.delete(`/cards/${id}`);

export const exportCards = (format = 'csv') => 
  api.get(`/cards/export/download?format=${format}`, {
    responseType: 'blob',
  });

// OCR相關API
export const ocrImage = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  return api.post('/ocr/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export default api; 
