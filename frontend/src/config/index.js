/**
 * 簡化的前端配置管理
 * 只使用環境變數進行配置
 */

// 環境類型檢測
const NODE_ENV = process.env.NODE_ENV || 'development';
const isDevelopment = NODE_ENV === 'development';
const isProduction = NODE_ENV === 'production';

// API 配置
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;
if (!API_BASE_URL) {
  console.error('❌ 缺少必要的環境變數: REACT_APP_API_BASE_URL');
  console.error('請檢查 .env 文件並確保設置了 API 基礎 URL');
}

// 輔助函數
const getBooleanEnv = (key, defaultValue = false) => {
  const value = process.env[key];
  if (value === undefined) return defaultValue;
  return value.toLowerCase() === 'true';
};

const getIntEnv = (key, defaultValue = 0) => {
  const value = process.env[key];
  if (value === undefined) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
};

// 配置常量
export const APP_NAME = process.env.REACT_APP_NAME || 'OCR 名片管理系統';
export const APP_VERSION = process.env.REACT_APP_VERSION || '1.0.0';
export const ENVIRONMENT = NODE_ENV;
export const API_TIMEOUT = getIntEnv('REACT_APP_API_TIMEOUT', 30000);

// 功能開關
export const DEBUG = getBooleanEnv('REACT_APP_DEBUG', isDevelopment);
export const ENABLE_DEV_TOOLS = getBooleanEnv('REACT_APP_ENABLE_DEV_TOOLS', isDevelopment);
export const ENABLE_ERROR_REPORTING = getBooleanEnv('REACT_APP_ENABLE_ERROR_REPORTING', false);

// 相機配置
export const CAMERA_DEFAULT_WIDTH = getIntEnv('REACT_APP_CAMERA_DEFAULT_WIDTH', 1920);
export const CAMERA_DEFAULT_HEIGHT = getIntEnv('REACT_APP_CAMERA_DEFAULT_HEIGHT', 1080);
export const CAMERA_TIMEOUT = getIntEnv('REACT_APP_CAMERA_TIMEOUT', 10000);

// UI 配置
export const PRIMARY_COLOR = process.env.REACT_APP_PRIMARY_COLOR || '#1890ff';
export const DEFAULT_PAGE_SIZE = getIntEnv('REACT_APP_DEFAULT_PAGE_SIZE', 20);
export const MAX_PAGE_SIZE = getIntEnv('REACT_APP_MAX_PAGE_SIZE', 100);

// 文件上傳配置
export const MAX_FILE_SIZE = getIntEnv('REACT_APP_MAX_FILE_SIZE', 10 * 1024 * 1024);
export const ALLOWED_IMAGE_TYPES = (process.env.REACT_APP_ALLOWED_IMAGE_TYPES || 'image/jpeg,image/jpg,image/png').split(',');

// 緩存配置
export const CACHE_EXPIRE_TIME = getIntEnv('REACT_APP_CACHE_EXPIRE_TIME', 3600000);
export const ENABLE_LOCAL_STORAGE = getBooleanEnv('REACT_APP_ENABLE_LOCAL_STORAGE', true);

// 環境檢查函數
export const isDev = () => isDevelopment;
export const isProd = () => isProduction;

// 配置驗證
export const validateConfig = () => {
  const errors = [];

  if (!API_BASE_URL) {
    errors.push('REACT_APP_API_BASE_URL 未設置');
  } else {
    try {
      new URL(API_BASE_URL);
    } catch (e) {
      errors.push('REACT_APP_API_BASE_URL 格式不正確');
    }
  }

  if (API_TIMEOUT < 1000) {
    errors.push('REACT_APP_API_TIMEOUT 不能小於 1000 毫秒');
  }

  if (MAX_FILE_SIZE < 1024) {
    errors.push('REACT_APP_MAX_FILE_SIZE 不能小於 1024 bytes');
  }

  if (errors.length > 0) {
    console.error('❌ 配置驗證失敗:', errors);
    return false;
  }

  return true;
};

// 打印配置摘要
export const printConfig = () => {
  if (!DEBUG) return;

  console.group('📋 前端配置');
  console.log('應用程式:', APP_NAME, 'v' + APP_VERSION);
  console.log('環境:', ENVIRONMENT);
  console.log('API URL:', API_BASE_URL);
  console.log('調試模式:', DEBUG);
  console.groupEnd();
};

// 默認導出 API_BASE_URL 用於向後兼容
export default API_BASE_URL;

// 在應用啟動時驗證配置
if (validateConfig()) {
  printConfig();
} else {
  console.error('🚨 前端配置有誤，請檢查環境變數設置');
}