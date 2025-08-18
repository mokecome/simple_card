/**
 * 設備和環境檢測工具
 * 用於識別運行環境並提供相應的功能支持檢測
 */

/**
 * 檢測是否可以使用DOM
 */
export const canUseDom = () => {
  return !!(typeof window !== 'undefined' && window.document && window.document.createElement);
};

/**
 * 檢測是否為移動設備
 */
export const isMobileDevice = () => {
  if (!canUseDom()) return false;
  
  const userAgent = navigator.userAgent || navigator.vendor || window.opera;
  
  // 檢測移動設備的用戶代理字符串
  const mobileRegex = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i;
  
  // 檢測觸摸支持
  const hasTouchSupport = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  
  // 檢測屏幕尺寸（移動設備通常寬度較小）
  const isSmallScreen = window.innerWidth <= 768;
  
  return mobileRegex.test(userAgent) || (hasTouchSupport && isSmallScreen);
};

/**
 * 檢測是否為Android設備
 */
export const isAndroid = () => {
  if (!canUseDom()) return false;
  return /android/i.test(navigator.userAgent);
};

/**
 * 檢測是否為iOS設備
 */
export const isIOS = () => {
  if (!canUseDom()) return false;
  return /ios|iphone|ipad|ipod/i.test(navigator.userAgent);
};

/**
 * 檢測是否為Web瀏覽器環境
 */
export const isWebBrowser = () => {
  return canUseDom() && !isMobileDevice();
};

/**
 * 檢測是否為平板設備
 */
export const isTablet = () => {
  if (!canUseDom()) return false;
  
  const userAgent = navigator.userAgent;
  const isTabletUA = /ipad|android(?!.*mobile)|tablet/i.test(userAgent);
  const isLargeScreen = window.innerWidth >= 768 && window.innerWidth <= 1024;
  
  return isTabletUA || (isMobileDevice() && isLargeScreen);
};

/**
 * 獲取設備類型
 */
export const getDeviceType = () => {
  if (isTablet()) return 'tablet';
  if (isMobileDevice()) return 'mobile';
  return 'desktop';
};

/**
 * 檢測相機功能支持
 */
export const getCameraCapabilities = async () => {
  const capabilities = {
    hasCamera: false,
    hasUserMedia: false,
    supportsFacingMode: false,
    supportsConstraints: false,
    availableCameras: []
  };

  if (!canUseDom() || !navigator.mediaDevices) {
    return capabilities;
  }

  try {
    // 檢測 getUserMedia 支持
    capabilities.hasUserMedia = !!navigator.mediaDevices.getUserMedia;

    if (capabilities.hasUserMedia) {
      // 嘗試獲取設備列表
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      
      capabilities.hasCamera = videoDevices.length > 0;
      capabilities.availableCameras = videoDevices.map(device => ({
        deviceId: device.deviceId,
        label: device.label || `Camera ${videoDevices.indexOf(device) + 1}`,
        groupId: device.groupId
      }));

      // 檢測是否支持 facingMode 約束
      if (capabilities.hasCamera) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' }
          });
          capabilities.supportsFacingMode = true;
          capabilities.supportsConstraints = true;
          
          // 立即停止測試流
          stream.getTracks().forEach(track => track.stop());
        } catch (error) {
          // 如果 facingMode 不支持，嘗試基本的視頻約束
          try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            capabilities.supportsConstraints = true;
            stream.getTracks().forEach(track => track.stop());
          } catch (basicError) {
            console.warn('基本相機功能不可用:', basicError);
          }
        }
      }
    }
  } catch (error) {
    console.warn('檢測相機功能時出錯:', error);
  }

  return capabilities;
};

/**
 * 檢測是否支持全屏API
 */
export const supportsFullscreen = () => {
  if (!canUseDom()) return false;
  
  return !!(
    document.fullscreenEnabled ||
    document.webkitFullscreenEnabled ||
    document.mozFullScreenEnabled ||
    document.msFullscreenEnabled
  );
};

/**
 * 檢測設備方向支持
 */
export const supportsOrientation = () => {
  if (!canUseDom()) return false;
  return 'orientation' in window || 'onorientationchange' in window;
};

/**
 * 獲取當前設備方向
 */
export const getDeviceOrientation = () => {
  if (!supportsOrientation()) return 'unknown';
  
  if (window.orientation !== undefined) {
    const orientation = Math.abs(window.orientation);
    return orientation === 90 ? 'landscape' : 'portrait';
  }
  
  // 備用方案：基於屏幕尺寸判斷
  return window.innerWidth > window.innerHeight ? 'landscape' : 'portrait';
};

/**
 * 綜合環境信息
 */
export const getEnvironmentInfo = async () => {
  const cameraCapabilities = await getCameraCapabilities();
  
  return {
    deviceType: getDeviceType(),
    isMobile: isMobileDevice(),
    isTablet: isTablet(),
    isDesktop: isWebBrowser(),
    isAndroid: isAndroid(),
    isIOS: isIOS(),
    orientation: getDeviceOrientation(),
    supportsFullscreen: supportsFullscreen(),
    supportsOrientation: supportsOrientation(),
    camera: cameraCapabilities,
    userAgent: canUseDom() ? navigator.userAgent : '',
    screenSize: canUseDom() ? {
      width: window.innerWidth,
      height: window.innerHeight,
      pixelRatio: window.devicePixelRatio || 1
    } : null
  };
};

/**
 * 推薦的拍照模式
 */
export const getRecommendedCameraMode = async () => {
  const envInfo = await getEnvironmentInfo();
  
  if (!envInfo.camera.hasCamera) {
    return 'none'; // 無相機支持
  }
  
  if (envInfo.isMobile || envInfo.isTablet) {
    return 'mobile'; // 移動端全屏模式
  }
  
  return 'web'; // Web端模態框模式
};

export default {
  canUseDom,
  isMobileDevice,
  isAndroid,
  isIOS,
  isWebBrowser,
  isTablet,
  getDeviceType,
  getCameraCapabilities,
  supportsFullscreen,
  supportsOrientation,
  getDeviceOrientation,
  getEnvironmentInfo,
  getRecommendedCameraMode
};
