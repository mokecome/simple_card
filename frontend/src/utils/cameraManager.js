/**
 * 統一相機管理器
 * 根據環境自動選擇合適的拍照策略，提供統一的API接口
 */

import { Toast } from 'antd-mobile';
import { getRecommendedCameraMode, getCameraCapabilities } from './deviceDetector';
import { createCameraStrategy } from './cameraStrategies';

/**
 * 相機管理器類
 */
class CameraManager {
  constructor() {
    this.strategy = null;
    this.mode = null;
    this.isInitialized = false;
    this.callbacks = {};
    this.capabilities = null;
  }

  /**
   * 初始化相機管理器
   */
  async initialize() {
    try {
      // 檢測相機功能
      this.capabilities = await getCameraCapabilities();
      
      if (!this.capabilities.hasCamera) {
        throw new Error('設備不支持相機功能');
      }

      // 獲取推薦的相機模式
      this.mode = await getRecommendedCameraMode();
      
      if (this.mode === 'none') {
        throw new Error('無可用的相機模式');
      }

      // 創建相應的策略
      this.strategy = createCameraStrategy(this.mode);
      
      // 設置策略回調
      this.strategy.setCallbacks({
        cameraStart: (data) => this.emit('cameraStart', data),
        cameraStop: () => this.emit('cameraStop'),
        cameraError: (error) => this.emit('cameraError', error),
        photoTaken: (data) => this.emit('photoTaken', data),
        photoError: (error) => this.emit('photoError', error),
        cameraSwitch: (data) => this.emit('cameraSwitch', data),
        cameraSwitchError: (error) => this.emit('cameraSwitchError', error)
      });

      this.isInitialized = true;
      console.log(`相機管理器初始化完成，模式: ${this.mode}`);
      
    } catch (error) {
      console.error('相機管理器初始化失敗:', error);
      throw error;
    }
  }

  /**
   * 設置事件回調
   */
  setCallbacks(callbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * 觸發事件回調
   */
  emit(event, data) {
    if (this.callbacks[event]) {
      this.callbacks[event](data);
    }
  }

  /**
   * 啟動相機
   */
  async startCamera(target = 'back', options = {}) {
    if (!this.isInitialized) {
      await this.initialize();
    }

    try {
      // 根據目標設置約束
      const constraints = this.buildConstraints(target, options);
      
      // 設置視頻和畫布元素（如果提供）
      if (options.videoElement && options.canvasElement) {
        this.strategy.setElements(options.videoElement, options.canvasElement);
      }

      const stream = await this.strategy.startCamera(constraints);
      
      this.emit('cameraStart', { 
        stream, 
        mode: this.mode, 
        target,
        capabilities: this.capabilities 
      });
      
      return stream;
    } catch (error) {
      console.error('啟動相機失敗:', error);
      
      // 用戶友好的錯誤提示
      let message = '無法啟動相機';
      if (error.name === 'NotAllowedError') {
        message = '相機權限被拒絕，請在瀏覽器設置中允許相機訪問';
      } else if (error.name === 'NotFoundError') {
        message = '未找到可用的相機設備';
      } else if (error.name === 'NotReadableError') {
        message = '相機被其他應用程序占用';
      }
      
      Toast.show({
        content: message,
        position: 'center'
      });
      
      this.emit('cameraError', error);
      throw error;
    }
  }

  /**
   * 停止相機
   */
  stopCamera() {
    if (this.strategy) {
      this.strategy.stopCamera();
    }
  }

  /**
   * 拍照
   */
  async takePhoto() {
    // 詳細的狀態檢查
    if (!this.isInitialized) {
      throw new Error('相機管理器未初始化');
    }

    if (!this.strategy) {
      throw new Error('相機策略未創建');
    }

    const strategyStatus = this.strategy.getStatus();
    if (!strategyStatus.isActive) {
      throw new Error('相機未啟動');
    }

    console.log('相機管理器開始拍照', {
      mode: this.mode,
      strategyStatus,
      capabilities: this.capabilities
    });

    try {
      const result = await this.strategy.takePhoto();

      if (!result || !result.file) {
        throw new Error('拍照結果無效');
      }

      const enhancedResult = {
        ...result,
        mode: this.mode,
        timestamp: new Date().toISOString(),
        deviceInfo: {
          userAgent: navigator.userAgent,
          screenSize: {
            width: window.innerWidth,
            height: window.innerHeight
          }
        }
      };

      console.log('相機管理器拍照成功', {
        fileSize: result.file.size,
        mode: this.mode,
        timestamp: enhancedResult.timestamp
      });

      this.emit('photoTaken', enhancedResult);

      return enhancedResult;
    } catch (error) {
      console.error('相機管理器拍照失敗:', error);

      Toast.show({
        content: `拍照失敗：${error.message || '請重試'}`,
        position: 'center'
      });

      this.emit('photoError', error);
      throw error;
    }
  }

  /**
   * 切換攝像頭（僅移動端支持）
   */
  async switchCamera() {
    if (!this.strategy) {
      throw new Error('相機未初始化');
    }

    if (this.mode !== 'mobile') {
      Toast.show({
        content: '當前模式不支持切換攝像頭',
        position: 'center'
      });
      return;
    }

    try {
      await this.strategy.switchCamera();
    } catch (error) {
      console.error('切換攝像頭失敗:', error);
      this.emit('cameraSwitchError', error);
    }
  }

  /**
   * 構建相機約束
   */
  buildConstraints(target, options) {
    const constraints = {
      video: {
        facingMode: target === 'front' ? 'user' : 'environment'
      }
    };

    // 根據模式調整約束
    if (this.mode === 'mobile') {
      // 移動端優化：嘗試獲取最高可用解析度
      constraints.video = {
        ...constraints.video,
        width: { ideal: 3840, min: 1920 }, // 4K優先，最低1080p
        height: { ideal: 2160, min: 1080 },
        frameRate: { ideal: 30, min: 15 },
        aspectRatio: { ideal: 16/9 }
      };
    } else {
      // Web端保持原有設置
      constraints.video = {
        ...constraints.video,
        width: { ideal: 1280 },
        height: { ideal: 720 }
      };
    }

    // 合併用戶提供的約束
    if (options.constraints) {
      constraints.video = {
        ...constraints.video,
        ...options.constraints.video
      };
    }

    return constraints;
  }

  /**
   * 獲取相機狀態
   */
  getStatus() {
    return {
      isInitialized: this.isInitialized,
      mode: this.mode,
      capabilities: this.capabilities,
      strategy: this.strategy ? this.strategy.getStatus() : null
    };
  }

  /**
   * 獲取當前模式
   */
  getMode() {
    return this.mode;
  }

  /**
   * 獲取相機功能
   */
  getCapabilities() {
    return this.capabilities;
  }

  /**
   * 檢查是否支持攝像頭切換
   */
  supportsCameraSwitch() {
    return this.mode === 'mobile' && 
           this.strategy && 
           typeof this.strategy.supportsCameraSwitch === 'function' && 
           this.strategy.supportsCameraSwitch();
  }

  /**
   * 銷毀管理器
   */
  destroy() {
    this.stopCamera();
    this.strategy = null;
    this.callbacks = {};
    this.isInitialized = false;
  }
}

// 創建單例實例
const cameraManager = new CameraManager();

/**
 * 獲取相機管理器實例
 */
export const getCameraManager = () => cameraManager;

/**
 * 便捷函數：初始化並啟動相機
 */
export const startCameraWithAutoDetection = async (target = 'back', options = {}) => {
  const manager = getCameraManager();
  return await manager.startCamera(target, options);
};

/**
 * 便捷函數：拍照
 */
export const takePhotoWithManager = async () => {
  const manager = getCameraManager();
  return await manager.takePhoto();
};

/**
 * 便捷函數：停止相機
 */
export const stopCameraWithManager = () => {
  const manager = getCameraManager();
  manager.stopCamera();
};

export default {
  CameraManager,
  getCameraManager,
  startCameraWithAutoDetection,
  takePhotoWithManager,
  stopCameraWithManager
};
