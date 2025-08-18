import axios from 'axios';
import { showError, showSuccess } from './errorHandler';
import config from '../config';

// 創建 axios 實例
const apiClient = axios.create({
  baseURL: config.api.baseUrl,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 請求攔截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在這裡添加認證 token
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    
    console.log('API Request:', {
      method: config.method,
      url: config.url,
      data: config.data
    });
    
    return config;
  },
  (error) => {
    console.error('請求配置錯誤:', error);
    return Promise.reject(error);
  }
);

// 響應攔截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('API Response:', {
      url: response.config.url,
      status: response.status,
      data: response.data
    });
    
    // 檢查後端統一響應格式
    if (response.data && typeof response.data === 'object') {
      // 新的統一響應格式
      if (response.data.hasOwnProperty('success')) {
        if (response.data.success) {
          return response.data.data || response.data;
        } else {
          // 後端返回失敗響應
          const errorMessage = response.data.message || '操作失敗';
          showError(errorMessage);
          return Promise.reject(new Error(errorMessage));
        }
      }
    }
    
    // 兼容舊格式或直接返回數據
    return response.data;
  },
  (error) => {
    console.error('API Error:', error);
    
    let errorMessage = '網絡錯誤，請稍後重試';
    
    if (error.response) {
      // 服務器響應了錯誤狀態碼
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          errorMessage = data?.message || '請求參數錯誤';
          break;
        case 401:
          errorMessage = '未授權，請重新登入';
          // 可以在這裡處理登出邏輯
          break;
        case 403:
          errorMessage = '權限不足';
          break;
        case 404:
          errorMessage = data?.message || '請求的資源不存在';
          break;
        case 422:
          errorMessage = data?.message || '數據驗證失敗';
          // 處理驗證錯誤詳情
          if (data?.error?.details) {
            console.error('驗證錯誤詳情:', data.error.details);
          }
          break;
        case 500:
          errorMessage = '服務器內部錯誤';
          break;
        default:
          errorMessage = data?.message || `請求失敗 (${status})`;
      }
    } else if (error.request) {
      // 請求已發送但沒有收到響應
      errorMessage = '無法連接到服務器，請檢查網絡連接';
    } else if (error.code === 'ECONNABORTED') {
      // 請求超時
      errorMessage = '請求超時，請稍後重試';
    }
    
    showError(errorMessage);
    return Promise.reject(error);
  }
);

// API 方法封裝
export const api = {
  // GET 請求
  get: (url, config = {}) => apiClient.get(url, config),
  
  // POST 請求
  post: (url, data = {}, config = {}) => apiClient.post(url, data, config),
  
  // PUT 請求
  put: (url, data = {}, config = {}) => apiClient.put(url, data, config),
  
  // DELETE 請求
  delete: (url, config = {}) => apiClient.delete(url, config),
  
  // 文件上傳專用方法
  uploadFile: (url, formData, config = {}) => {
    const uploadConfig = {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config.headers,
      },
      timeout: 60000, // 文件上傳超時設置為60秒
    };
    
    return apiClient.post(url, formData, uploadConfig);
  },
  
  // 下載文件專用方法
  downloadFile: (url, config = {}) => {
    const downloadConfig = {
      ...config,
      responseType: 'blob',
    };
    
    return apiClient.get(url, downloadConfig);
  }
};

export default apiClient;