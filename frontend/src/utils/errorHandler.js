import { Toast } from 'antd-mobile';

// 錯誤代碼映射到用戶友好的繁體中文消息
const ERROR_MESSAGES = {
  // 名片相關錯誤
  'CARD_NOT_FOUND': '找不到指定的名片',
  'CARD_CREATE_FAILED': '創建名片失敗，請稍後重試',
  'CARD_UPDATE_FAILED': '更新名片失敗，請稍後重試',
  'CARD_DELETE_FAILED': '刪除名片失敗，請稍後重試',
  
  // OCR相關錯誤
  'OCR_SERVICE_UNAVAILABLE': 'OCR服務暫時不可用，請稍後重試',
  'OCR_PARSE_FAILED': 'OCR解析失敗，請嘗試更清晰的圖像',
  
  // 文件相關錯誤
  'FILE_UPLOAD_FAILED': '文件上傳失敗，請檢查網絡連接',
  'FILE_TYPE_NOT_SUPPORTED': '不支持的文件類型',
  
  // 系統錯誤
  'INTERNAL_SERVER_ERROR': '系統內部錯誤，請聯繫管理員',
  'VALIDATION_ERROR': '輸入的數據格式不正確',
  'DATABASE_ERROR': '數據庫操作失敗，請稍後重試',
  
  // 網絡錯誤
  'NETWORK_ERROR': '網絡連接失敗，請檢查網絡設置',
  'TIMEOUT_ERROR': '請求超時，請稍後重試',
  
  // 默認錯誤
  'UNKNOWN_ERROR': '發生未知錯誤，請稍後重試'
};

// 錯誤級別
const ERROR_LEVELS = {
  INFO: 'info',
  WARN: 'warn',
  ERROR: 'error',
  CRITICAL: 'critical'
};

// 需要自動重試的錯誤類型
const RETRYABLE_ERRORS = [
  'NETWORK_ERROR',
  'TIMEOUT_ERROR',
  'OCR_SERVICE_UNAVAILABLE',
  'DATABASE_ERROR'
];

class ErrorHandler {
  constructor() {
    this.retryAttempts = new Map(); // 追蹤重試次數
    this.maxRetries = 3;
    this.retryDelay = 1000; // 1秒
  }

  /**
   * 處理API錯誤響應
   * @param {Error} error - 錯誤對象
   * @param {Object} context - 上下文信息
   * @param {Function} retryFunction - 重試函數
   */
  handleError = (error, context = {}, retryFunction = null) => {
    console.error('錯誤詳情:', error, '上下文:', context);
    
    const errorInfo = this.parseError(error);
    
    // 記錄錯誤到控制台（開發環境）
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 錯誤處理');
      console.error('錯誤代碼:', errorInfo.code);
      console.error('錯誤消息:', errorInfo.message);
      console.error('追蹤ID:', errorInfo.traceId);
      console.error('原始錯誤:', error);
      console.groupEnd();
    }
    
    // 根據錯誤級別決定處理方式
    switch (errorInfo.level) {
      case ERROR_LEVELS.INFO:
        this.showInfoMessage(errorInfo.userMessage);
        break;
      case ERROR_LEVELS.WARN:
        this.showWarningMessage(errorInfo.userMessage);
        break;
      case ERROR_LEVELS.ERROR:
        this.showErrorMessage(errorInfo.userMessage);
        this.handleRetry(errorInfo, retryFunction, context);
        break;
      case ERROR_LEVELS.CRITICAL:
        this.showCriticalError(errorInfo);
        break;
      default:
        this.showErrorMessage(errorInfo.userMessage);
    }
    
    // 上報錯誤（生產環境）
    if (process.env.NODE_ENV === 'production') {
      this.reportError(errorInfo, context);
    }
    
    return errorInfo;
  };

  /**
   * 解析錯誤對象
   * @param {Error} error - 錯誤對象
   * @returns {Object} 解析後的錯誤信息
   */
  parseError = (error) => {
    let code = 'UNKNOWN_ERROR';
    let message = '發生未知錯誤';
    let level = ERROR_LEVELS.ERROR;
    let traceId = null;
    let details = null;

    if (error.response) {
      // HTTP響應錯誤
      const responseData = error.response.data;
      
      if (responseData && responseData.error) {
        // 標準化的錯誤響應格式
        code = responseData.error.code || 'UNKNOWN_ERROR';
        message = responseData.error.message || ERROR_MESSAGES[code] || ERROR_MESSAGES['UNKNOWN_ERROR'];
        traceId = responseData.error.trace_id;
        details = responseData.error.details;
      } else {
        // 原始HTTP錯誤
        const status = error.response.status;
        switch (status) {
          case 400:
            code = 'VALIDATION_ERROR';
            level = ERROR_LEVELS.WARN;
            break;
          case 401:
            code = 'UNAUTHORIZED';
            message = '未授權訪問';
            level = ERROR_LEVELS.WARN;
            break;
          case 403:
            code = 'FORBIDDEN';
            message = '訪問被拒絕';
            level = ERROR_LEVELS.WARN;
            break;
          case 404:
            code = 'NOT_FOUND';
            message = '請求的資源不存在';
            level = ERROR_LEVELS.WARN;
            break;
          case 500:
            code = 'INTERNAL_SERVER_ERROR';
            level = ERROR_LEVELS.CRITICAL;
            break;
          default:
            code = 'HTTP_ERROR';
            message = `HTTP錯誤 ${status}`;
        }
      }
    } else if (error.request) {
      // 網絡錯誤
      code = 'NETWORK_ERROR';
      level = ERROR_LEVELS.ERROR;
    } else if (error.code === 'ECONNABORTED') {
      // 超時錯誤
      code = 'TIMEOUT_ERROR';
      level = ERROR_LEVELS.ERROR;
    }

    const userMessage = ERROR_MESSAGES[code] || ERROR_MESSAGES['UNKNOWN_ERROR'];

    return {
      code,
      message,
      userMessage,
      level,
      traceId,
      details,
      originalError: error
    };
  };

  /**
   * 處理重試邏輯
   * @param {Object} errorInfo - 錯誤信息
   * @param {Function} retryFunction - 重試函數
   * @param {Object} context - 上下文
   */
  handleRetry = (errorInfo, retryFunction, context) => {
    if (!retryFunction || !RETRYABLE_ERRORS.includes(errorInfo.code)) {
      return;
    }

    const key = `${context.action}_${Date.now()}`;
    const attempts = this.retryAttempts.get(key) || 0;

    if (attempts < this.maxRetries) {
      this.retryAttempts.set(key, attempts + 1);
      
      setTimeout(() => {
        console.log(`重試第 ${attempts + 1} 次: ${errorInfo.code}`);
        retryFunction()
          .then(() => {
            this.retryAttempts.delete(key);
            Toast.show({
              icon: 'success',
              content: '操作成功'
            });
          })
          .catch((retryError) => {
            this.handleError(retryError, context, retryFunction);
          });
      }, this.retryDelay * Math.pow(2, attempts)); // 指數退避
    } else {
      this.retryAttempts.delete(key);
      Toast.show({
        icon: 'fail',
        content: `${errorInfo.userMessage}（已重試${this.maxRetries}次）`
      });
    }
  };

  /**
   * 顯示信息消息
   */
  showInfoMessage = (message) => {
    Toast.show({
      icon: 'success',
      content: message
    });
  };

  /**
   * 顯示警告消息
   */
  showWarningMessage = (message) => {
    Toast.show({
      icon: 'loading',
      content: message
    });
  };

  /**
   * 顯示錯誤消息
   */
  showErrorMessage = (message) => {
    Toast.show({
      icon: 'fail',
      content: message,
      duration: 3000
    });
  };

  /**
   * 顯示嚴重錯誤
   */
  showCriticalError = (errorInfo) => {
    Toast.show({
      icon: 'fail',
      content: `${errorInfo.userMessage}${errorInfo.traceId ? `\n追蹤ID: ${errorInfo.traceId}` : ''}`,
      duration: 5000
    });
  };

  /**
   * 上報錯誤到監控系統
   */
  reportError = (errorInfo, context) => {
    // 這裡可以集成錯誤監控服務如 Sentry
    const errorReport = {
      timestamp: new Date().toISOString(),
      code: errorInfo.code,
      message: errorInfo.message,
      traceId: errorInfo.traceId,
      context,
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    // 發送到監控服務（示例）
    // fetch('/api/errors', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(errorReport)
    // });

    console.log('錯誤報告:', errorReport);
  };

  /**
   * 清理重試記錄
   */
  cleanup = () => {
    this.retryAttempts.clear();
  };
}

// 導出單例實例
const errorHandler = new ErrorHandler();

// 便捷方法
export const handleApiError = (error, context, retryFunction) => {
  return errorHandler.handleError(error, context, retryFunction);
};

export const showSuccess = (message) => {
  Toast.show({
    icon: 'success',
    content: message
  });
};

export const showError = (message) => {
  Toast.show({
    icon: 'fail',
    content: message
  });
};

export const showLoading = (message = '處理中...') => {
  return Toast.show({
    icon: 'loading',
    content: message,
    duration: 0
  });
};

export default errorHandler; 