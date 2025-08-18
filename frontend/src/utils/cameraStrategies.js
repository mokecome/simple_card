/**
 * 相機拍照策略實現
 * 根據不同的運行環境提供相應的拍照功能
 */

import { Toast } from 'antd-mobile';

/**
 * 基礎相機策略抽象類
 */
class BaseCameraStrategy {
  constructor() {
    this.stream = null;
    this.isActive = false;
    this.callbacks = {};
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
   * 啟動相機 - 子類需要實現
   */
  async startCamera(constraints) {
    throw new Error('startCamera method must be implemented');
  }

  /**
   * 停止相機
   */
  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.isActive = false;
    this.emit('cameraStop');
  }

  /**
   * 拍照 - 子類需要實現
   */
  async takePhoto() {
    throw new Error('takePhoto method must be implemented');
  }

  /**
   * 切換攝像頭
   */
  async switchCamera() {
    // 默認實現，子類可以覆蓋
    console.warn('Camera switching not implemented for this strategy');
  }

  /**
   * 獲取相機狀態
   */
  getStatus() {
    return {
      isActive: this.isActive,
      hasStream: !!this.stream
    };
  }
}

/**
 * Web端相機策略 - 使用Modal模式
 */
export class WebCameraStrategy extends BaseCameraStrategy {
  constructor() {
    super();
    this.videoElement = null;
    this.canvasElement = null;
  }

  /**
   * 設置視頻和畫布元素
   */
  setElements(videoElement, canvasElement) {
    this.videoElement = videoElement;
    this.canvasElement = canvasElement;
  }

  /**
   * 啟動相機
   */
  async startCamera(constraints = {}) {
    try {
      const defaultConstraints = {
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };

      const finalConstraints = {
        ...defaultConstraints,
        ...constraints
      };

      console.log('Web相機啟動中...', { constraints: finalConstraints });

      this.stream = await navigator.mediaDevices.getUserMedia(finalConstraints);

      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;

        // 等待視頻元素準備就緒
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('視頻加載超時'));
          }, 5000);

          const onLoadedData = () => {
            clearTimeout(timeout);
            this.videoElement.removeEventListener('loadeddata', onLoadedData);
            this.videoElement.removeEventListener('error', onError);
            console.log('Web相機視頻加載完成', {
              videoWidth: this.videoElement.videoWidth,
              videoHeight: this.videoElement.videoHeight
            });
            resolve();
          };

          const onError = (error) => {
            clearTimeout(timeout);
            this.videoElement.removeEventListener('loadeddata', onLoadedData);
            this.videoElement.removeEventListener('error', onError);
            reject(error);
          };

          this.videoElement.addEventListener('loadeddata', onLoadedData);
          this.videoElement.addEventListener('error', onError);
        });
      }

      this.isActive = true;
      this.emit('cameraStart', { stream: this.stream });

      console.log('Web相機啟動成功');
      return this.stream;
    } catch (error) {
      console.error('Web相機啟動失敗:', error);
      this.emit('cameraError', error);
      throw error;
    }
  }

  /**
   * 檢查視頻是否準備就緒
   */
  isVideoReady() {
    if (!this.videoElement) return false;

    const video = this.videoElement;
    return video.readyState >= 2 && // HAVE_CURRENT_DATA
           video.videoWidth > 0 &&
           video.videoHeight > 0 &&
           !video.paused &&
           !video.ended;
  }

  /**
   * 等待視頻準備就緒
   */
  async waitForVideoReady(timeout = 5000) {
    return new Promise((resolve, reject) => {
      if (this.isVideoReady()) {
        resolve();
        return;
      }

      const startTime = Date.now();
      const checkReady = () => {
        if (this.isVideoReady()) {
          resolve();
        } else if (Date.now() - startTime > timeout) {
          reject(new Error('視頻準備超時'));
        } else {
          setTimeout(checkReady, 100);
        }
      };

      // 監聽視頻事件
      if (this.videoElement) {
        const onReady = () => {
          if (this.isVideoReady()) {
            this.videoElement.removeEventListener('loadeddata', onReady);
            this.videoElement.removeEventListener('canplay', onReady);
            resolve();
          }
        };

        this.videoElement.addEventListener('loadeddata', onReady);
        this.videoElement.addEventListener('canplay', onReady);
      }

      checkReady();
    });
  }

  /**
   * 拍照
   */
  async takePhoto() {
    if (!this.videoElement || !this.canvasElement || !this.isActive) {
      throw new Error('相機未準備就緒');
    }

    try {
      // 等待視頻準備就緒
      await this.waitForVideoReady();

      const video = this.videoElement;
      const canvas = this.canvasElement;
      const context = canvas.getContext('2d');

      // 檢查視頻尺寸
      if (video.videoWidth === 0 || video.videoHeight === 0) {
        throw new Error('視頻尺寸無效');
      }

      // 設置畫布尺寸
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      console.log(`Web拍照 - 視頻尺寸: ${video.videoWidth}x${video.videoHeight}`);

      // 設置高質量渲染
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = 'high';
      
      // 輕微圖像增強（適度，保持自然）
      if (video.videoWidth >= 1280 && video.videoHeight >= 720) {
        context.filter = 'contrast(1.04) brightness(1.02) saturate(1.02)';
      }

      // 繪製視頻幀到畫布
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // 轉換為Blob，使用高質量設置
      return new Promise((resolve, reject) => {
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], 'web-photo-enhanced.jpg', { type: 'image/jpeg' });
            console.log(`Web拍照成功 - 文件大小: ${blob.size} bytes`);
            this.emit('photoTaken', { file, blob });
            resolve({ file, blob });
          } else {
            reject(new Error('無法生成照片'));
          }
        }, 'image/jpeg', 0.92); // 稍微提高質量
      });
    } catch (error) {
      console.error('Web拍照失敗:', error);
      this.emit('photoError', error);
      throw error;
    }
  }
}

/**
 * 移動端相機策略 - 全屏模式
 */
export class MobileCameraStrategy extends BaseCameraStrategy {
  constructor() {
    super();
    this.videoElement = null;
    this.canvasElement = null;
    this.currentFacingMode = 'environment'; // 默認後置攝像頭
    this.supportsFacingMode = true;
  }

  /**
   * 設置視頻和畫布元素
   */
  setElements(videoElement, canvasElement) {
    this.videoElement = videoElement;
    this.canvasElement = canvasElement;
  }

  /**
   * 獲取最佳相機約束
   */
  getBestCameraConstraints() {
    // 嘗試獲取設備支持的最高解析度
    const highResConstraints = {
      video: {
        facingMode: this.currentFacingMode,
        width: { ideal: 3840, min: 1920 }, // 4K優先，最低1080p
        height: { ideal: 2160, min: 1080 },
        frameRate: { ideal: 30, min: 15 },
        aspectRatio: { ideal: 16/9 }
      }
    };

    const standardConstraints = {
      video: {
        facingMode: this.currentFacingMode,
        width: { ideal: 2560, min: 1280 }, // 2K優先，最低720p
        height: { ideal: 1440, min: 720 },
        frameRate: { ideal: 30, min: 15 }
      }
    };

    const fallbackConstraints = {
      video: {
        facingMode: this.currentFacingMode,
        width: { ideal: 1920, min: 1280 },
        height: { ideal: 1080, min: 720 }
      }
    };

    return { highResConstraints, standardConstraints, fallbackConstraints };
  }

  /**
   * 啟動相機
   */
  async startCamera(constraints = {}) {
    try {
      const { highResConstraints, standardConstraints, fallbackConstraints } = this.getBestCameraConstraints();

      // 如果用戶提供了自定義約束，使用用戶約束
      if (constraints.video) {
        const finalConstraints = {
          video: {
            ...standardConstraints.video,
            ...constraints.video
          }
        };
        return await this.attemptCameraStart(finalConstraints);
      }

      // 嘗試不同解析度級別
      const constraintLevels = [
        { name: '4K/高解析度', constraints: highResConstraints },
        { name: '2K/標準解析度', constraints: standardConstraints },
        { name: '1080p/備用解析度', constraints: fallbackConstraints }
      ];

      for (const level of constraintLevels) {
        try {
          console.log(`移動端嘗試${level.name}相機啟動...`);
          return await this.attemptCameraStart(level.constraints);
        } catch (error) {
          console.warn(`${level.name}啟動失敗，嘗試下一級別:`, error.message);
          continue;
        }
      }

      // 如果所有預設都失敗，嘗試基本約束
      throw new Error('所有解析度級別都無法啟動相機');

    } catch (error) {
      console.error('移動端相機啟動失敗:', error);

      // 如果指定的攝像頭模式失敗，嘗試基本模式
      if (error.name === 'OverconstrainedError' && this.currentFacingMode !== 'user') {
        try {
          this.currentFacingMode = 'user';
          return await this.startCamera({ video: { facingMode: 'user' } });
        } catch (fallbackError) {
          this.supportsFacingMode = false;
          return await this.startCamera({ video: true });
        }
      }

      this.emit('cameraError', error);
      throw error;
    }
  }

  /**
   * 嘗試啟動相機的核心方法
   */
  async attemptCameraStart(finalConstraints) {
    try {
      console.log('移動端相機啟動中...', { constraints: finalConstraints });

      this.stream = await navigator.mediaDevices.getUserMedia(finalConstraints);

      // 記錄實際獲得的解析度
      if (this.stream) {
        const videoTrack = this.stream.getVideoTracks()[0];
        if (videoTrack) {
          const settings = videoTrack.getSettings();
          console.log('移動端相機實際解析度:', {
            width: settings.width,
            height: settings.height,
            frameRate: settings.frameRate,
            facingMode: settings.facingMode
          });
        }
      }
      
      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;

        // 移動端優化：設置視頻屬性
        this.videoElement.setAttribute('playsinline', true);
        this.videoElement.setAttribute('webkit-playsinline', true);
        this.videoElement.muted = true;

        // 等待視頻元素準備就緒
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('移動端視頻加載超時'));
          }, 8000); // 移動端給更多時間

          const onLoadedData = () => {
            clearTimeout(timeout);
            this.videoElement.removeEventListener('loadeddata', onLoadedData);
            this.videoElement.removeEventListener('error', onError);
            console.log('移動端相機視頻加載完成', {
              videoWidth: this.videoElement.videoWidth,
              videoHeight: this.videoElement.videoHeight,
              facingMode: this.currentFacingMode
            });
            resolve();
          };

          const onError = (error) => {
            clearTimeout(timeout);
            this.videoElement.removeEventListener('loadeddata', onLoadedData);
            this.videoElement.removeEventListener('error', onError);
            reject(error);
          };

          this.videoElement.addEventListener('loadeddata', onLoadedData);
          this.videoElement.addEventListener('error', onError);
        });
      }

      this.isActive = true;
      this.emit('cameraStart', { 
        stream: this.stream, 
        facingMode: this.currentFacingMode 
      });
      
      return this.stream;
    } catch (error) {
      console.error('移動端相機啟動失敗:', error);
      
      // 如果指定的攝像頭模式失敗，嘗試基本模式
      if (error.name === 'OverconstrainedError' && this.currentFacingMode !== 'user') {
        try {
          this.currentFacingMode = 'user';
          return await this.startCamera({ video: { facingMode: 'user' } });
        } catch (fallbackError) {
          this.supportsFacingMode = false;
          return await this.startCamera({ video: true });
        }
      }
      
      this.emit('cameraError', error);
      throw error;
    }
  }

  /**
   * 切換前後攝像頭
   */
  async switchCamera() {
    if (!this.supportsFacingMode) {
      Toast.show({
        content: '此設備不支持切換攝像頭',
        position: 'center'
      });
      return;
    }

    try {
      // 停止當前流
      this.stopCamera();
      
      // 切換攝像頭模式
      this.currentFacingMode = this.currentFacingMode === 'environment' ? 'user' : 'environment';
      
      // 重新啟動相機
      await this.startCamera();
      
      this.emit('cameraSwitch', { facingMode: this.currentFacingMode });
      
      Toast.show({
        content: `已切換到${this.currentFacingMode === 'environment' ? '後置' : '前置'}攝像頭`,
        position: 'center'
      });
    } catch (error) {
      console.error('切換攝像頭失敗:', error);
      Toast.show({
        content: '切換攝像頭失敗，請重試',
        position: 'center'
      });
      this.emit('cameraSwitchError', error);
    }
  }

  /**
   * 檢查視頻是否準備就緒
   */
  isVideoReady() {
    if (!this.videoElement) return false;

    const video = this.videoElement;
    return video.readyState >= 2 && // HAVE_CURRENT_DATA
           video.videoWidth > 0 &&
           video.videoHeight > 0 &&
           !video.paused &&
           !video.ended;
  }

  /**
   * 等待視頻準備就緒並確保對焦穩定
   */
  async waitForVideoReady() {
    const video = this.videoElement;
    if (!video) {
      throw new Error('視頻元素不存在');
    }

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('視頻準備超時'));
      }, 10000);

      const checkReady = () => {
        if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
          clearTimeout(timeout);
          resolve();
        } else {
          setTimeout(checkReady, 50);
        }
      };

      checkReady();
    });
  }

  /**
   * 確保拍攝穩定性
   */
  async ensureStability() {
    // 等待設備穩定（減少手震影響）
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // 檢查視頻流是否穩定
    const video = this.videoElement;
    if (video && video.srcObject) {
      const tracks = video.srcObject.getVideoTracks();
      if (tracks.length > 0) {
        const track = tracks[0];
        const settings = track.getSettings();
        
        // 記錄當前設置
        console.log('拍攝穩定性檢查:', {
          width: settings.width,
          height: settings.height,
          frameRate: settings.frameRate,
          readyState: video.readyState
        });
      }
    }
  }

  /**
   * 優化畫布渲染設置
   */
  optimizeCanvasRendering(context, videoWidth, videoHeight) {
    // 啟用高質量渲染
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';

    // 針對高解析度進行優化
    if (videoWidth >= 2560 || videoHeight >= 1440) {
      // 高解析度時使用更精細的渲染設置
      context.globalCompositeOperation = 'source-over';
      
      // 輕微增強對比度和銳化，有利於OCR識別
      context.filter = 'contrast(1.08) brightness(1.03) saturate(1.05) sepia(0) hue-rotate(0deg)';
    } else if (videoWidth >= 1920 || videoHeight >= 1080) {
      // 中等解析度優化
      context.filter = 'contrast(1.06) brightness(1.02) saturate(1.03)';
    } else {
      // 標準解析度優化
      context.filter = 'contrast(1.04) brightness(1.01) saturate(1.02)';
    }
  }

  /**
   * 高級圖像後處理
   */
  async postProcessImage(canvas, context) {
    // 創建臨時畫布進行圖像處理
    const tempCanvas = document.createElement('canvas');
    const tempContext = tempCanvas.getContext('2d');
    
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    
    // 複製原圖像
    tempContext.drawImage(canvas, 0, 0);
    
    // 獲取圖像數據
    const imageData = tempContext.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    
    // 輕微銳化處理（增強文字邊緣）
    const sharpenKernel = [
      0, -0.2, 0,
      -0.2, 1.8, -0.2,
      0, -0.2, 0
    ];
    
    // 應用銳化濾鏡（僅對高解析度圖像）
    if (canvas.width >= 1920 && canvas.height >= 1080) {
      this.applySharpenFilter(data, canvas.width, canvas.height, sharpenKernel);
    }
    
    // 輕微對比度增強
    for (let i = 0; i < data.length; i += 4) {
      // 增強對比度，但保持自然度
      data[i] = Math.min(255, Math.max(0, (data[i] - 128) * 1.15 + 128));     // R
      data[i + 1] = Math.min(255, Math.max(0, (data[i + 1] - 128) * 1.15 + 128)); // G
      data[i + 2] = Math.min(255, Math.max(0, (data[i + 2] - 128) * 1.15 + 128)); // B
    }
    
    // 將處理後的數據重新繪製到畫布
    tempContext.putImageData(imageData, 0, 0);
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.drawImage(tempCanvas, 0, 0);
    
    return canvas;
  }

  /**
   * 應用銳化濾鏡
   */
  applySharpenFilter(data, width, height, kernel) {
    const tempData = new Uint8ClampedArray(data);
    
    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        for (let c = 0; c < 3; c++) { // RGB通道
          let sum = 0;
          for (let ky = -1; ky <= 1; ky++) {
            for (let kx = -1; kx <= 1; kx++) {
              const idx = ((y + ky) * width + (x + kx)) * 4 + c;
              sum += tempData[idx] * kernel[(ky + 1) * 3 + (kx + 1)];
            }
          }
          const idx = (y * width + x) * 4 + c;
          data[idx] = Math.min(255, Math.max(0, sum));
        }
      }
    }
  }

  /**
   * 獲取最佳圖片質量設置
   */
  getOptimalImageQuality(videoWidth, videoHeight) {
    const totalPixels = videoWidth * videoHeight;

    // 根據解析度動態調整質量和壓縮策略
    if (totalPixels >= 3840 * 2160) { // 4K及以上
      return {
        quality: 0.98, // 最高質量
        maxFileSize: 8 * 1024 * 1024, // 8MB
        compressionLevel: 'minimal'
      };
    } else if (totalPixels >= 2560 * 1440) { // 2K
      return {
        quality: 0.97,
        maxFileSize: 6 * 1024 * 1024, // 6MB
        compressionLevel: 'low'
      };
    } else if (totalPixels >= 1920 * 1080) { // 1080p
      return {
        quality: 0.96,
        maxFileSize: 4 * 1024 * 1024, // 4MB
        compressionLevel: 'medium'
      };
    } else { // 720p及以下
      return {
        quality: 0.95,
        maxFileSize: 2 * 1024 * 1024, // 2MB
        compressionLevel: 'standard'
      };
    }
  }

  /**
   * 拍照
   */
  async takePhoto() {
    if (!this.videoElement || !this.canvasElement || !this.isActive) {
      throw new Error('相機未準備就緒');
    }

    try {
      // 確保拍攝穩定性
      await this.ensureStability();
      
      // 等待視頻準備就緒
      await this.waitForVideoReady();

      const video = this.videoElement;
      const canvas = this.canvasElement;
      const context = canvas.getContext('2d');

      // 檢查視頻尺寸
      if (video.videoWidth === 0 || video.videoHeight === 0) {
        throw new Error('視頻尺寸無效');
      }

      // 設置畫布尺寸為視頻的實際尺寸
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      console.log(`移動端拍照 - 視頻尺寸: ${video.videoWidth}x${video.videoHeight}, 攝像頭: ${this.currentFacingMode}`);

      // 優化畫布渲染設置
      this.optimizeCanvasRendering(context, video.videoWidth, video.videoHeight);

      // 繪製視頻幀到畫布
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // 進行圖像後處理
      await this.postProcessImage(canvas, context);

      // 獲取最佳圖片質量設置
      const qualitySettings = this.getOptimalImageQuality(video.videoWidth, video.videoHeight);

      console.log(`移動端拍照質量設置:`, qualitySettings);

      // 移動端優化：動態質量壓縮
      return new Promise((resolve, reject) => {
        canvas.toBlob((blob) => {
          if (blob) {
            // 檢查文件大小，如果超過限制則降低質量重新壓縮
            if (blob.size > qualitySettings.maxFileSize && qualitySettings.quality > 0.85) {
              console.log(`文件過大 (${blob.size} bytes)，重新壓縮...`);

              // 降低質量重新壓縮
              const reducedQuality = Math.max(0.85, qualitySettings.quality - 0.1);
              canvas.toBlob((reducedBlob) => {
                if (reducedBlob) {
                  const file = new File([reducedBlob], 'mobile-photo-enhanced.jpg', { type: 'image/jpeg' });
                  console.log(`移動端拍照成功 (重新壓縮) - 文件大小: ${reducedBlob.size} bytes, 質量: ${reducedQuality}, 攝像頭: ${this.currentFacingMode}`);
                  this.emit('photoTaken', { file, blob: reducedBlob, facingMode: this.currentFacingMode });
                  resolve({ file, blob: reducedBlob, facingMode: this.currentFacingMode });
                } else {
                  reject(new Error('重新壓縮失敗'));
                }
              }, 'image/jpeg', reducedQuality);
            } else {
              const file = new File([blob], 'mobile-photo-enhanced.jpg', { type: 'image/jpeg' });
              console.log(`移動端拍照成功 - 文件大小: ${blob.size} bytes, 質量: ${qualitySettings.quality}, 攝像頭: ${this.currentFacingMode}`);
              this.emit('photoTaken', { file, blob, facingMode: this.currentFacingMode });
              resolve({ file, blob, facingMode: this.currentFacingMode });
            }
          } else {
            reject(new Error('無法生成照片'));
          }
        }, 'image/jpeg', qualitySettings.quality);
      });
    } catch (error) {
      console.error('移動端拍照失敗:', error);
      this.emit('photoError', error);
      throw error;
    }
  }

  /**
   * 獲取當前攝像頭模式
   */
  getCurrentFacingMode() {
    return this.currentFacingMode;
  }

  /**
   * 檢查是否支持攝像頭切換
   */
  supportsCameraSwitch() {
    return this.supportsFacingMode;
  }
}

/**
 * 策略工廠函數
 */
export const createCameraStrategy = (mode) => {
  switch (mode) {
    case 'web':
      return new WebCameraStrategy();
    case 'mobile':
      return new MobileCameraStrategy();
    default:
      throw new Error(`不支持的相機模式: ${mode}`);
  }
};

export default {
  WebCameraStrategy,
  MobileCameraStrategy,
  createCameraStrategy
};
