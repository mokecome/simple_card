/**
 * 相機系統測試文件
 * 測試環境檢測和相機功能
 */

import { 
  isMobileDevice, 
  isWebBrowser, 
  getDeviceType, 
  getRecommendedCameraMode,
  getCameraCapabilities 
} from '../deviceDetector';
import { createCameraStrategy } from '../cameraStrategies';
import { getCameraManager } from '../cameraManager';

// Mock navigator 和 window 對象
const mockNavigator = {
  userAgent: '',
  mediaDevices: {
    getUserMedia: jest.fn(),
    enumerateDevices: jest.fn()
  }
};

const mockWindow = {
  innerWidth: 1024,
  innerHeight: 768,
  devicePixelRatio: 1
};

// 設置全局 mocks
global.navigator = mockNavigator;
global.window = mockWindow;

describe('設備檢測功能', () => {
  beforeEach(() => {
    // 重置 mocks
    mockNavigator.userAgent = '';
    mockWindow.innerWidth = 1024;
    mockWindow.innerHeight = 768;
  });

  test('應該正確檢測桌面設備', () => {
    mockNavigator.userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
    mockWindow.innerWidth = 1920;
    mockWindow.innerHeight = 1080;

    expect(isMobileDevice()).toBe(false);
    expect(isWebBrowser()).toBe(true);
    expect(getDeviceType()).toBe('desktop');
  });

  test('應該正確檢測移動設備', () => {
    mockNavigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)';
    mockWindow.innerWidth = 375;
    mockWindow.innerHeight = 812;

    expect(isMobileDevice()).toBe(true);
    expect(isWebBrowser()).toBe(false);
    expect(getDeviceType()).toBe('mobile');
  });

  test('應該正確檢測Android設備', () => {
    mockNavigator.userAgent = 'Mozilla/5.0 (Linux; Android 10; SM-G975F)';
    mockWindow.innerWidth = 360;
    mockWindow.innerHeight = 760;

    expect(isMobileDevice()).toBe(true);
    expect(getDeviceType()).toBe('mobile');
  });

  test('應該正確檢測平板設備', () => {
    mockNavigator.userAgent = 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)';
    mockWindow.innerWidth = 768;
    mockWindow.innerHeight = 1024;

    expect(getDeviceType()).toBe('tablet');
  });
});

describe('相機功能檢測', () => {
  beforeEach(() => {
    // 重置 mediaDevices mocks
    mockNavigator.mediaDevices.getUserMedia.mockReset();
    mockNavigator.mediaDevices.enumerateDevices.mockReset();
  });

  test('應該檢測到相機支持', async () => {
    // Mock 成功的相機檢測
    mockNavigator.mediaDevices.enumerateDevices.mockResolvedValue([
      { kind: 'videoinput', deviceId: 'camera1', label: 'Front Camera' },
      { kind: 'videoinput', deviceId: 'camera2', label: 'Back Camera' }
    ]);
    
    mockNavigator.mediaDevices.getUserMedia.mockResolvedValue({
      getTracks: () => [{ stop: jest.fn() }]
    });

    const capabilities = await getCameraCapabilities();
    
    expect(capabilities.hasCamera).toBe(true);
    expect(capabilities.hasUserMedia).toBe(true);
    expect(capabilities.availableCameras).toHaveLength(2);
  });

  test('應該處理無相機設備', async () => {
    // Mock 無相機設備
    mockNavigator.mediaDevices.enumerateDevices.mockResolvedValue([]);
    
    const capabilities = await getCameraCapabilities();
    
    expect(capabilities.hasCamera).toBe(false);
    expect(capabilities.availableCameras).toHaveLength(0);
  });

  test('應該推薦正確的相機模式', async () => {
    // Mock 移動設備
    mockNavigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)';
    mockWindow.innerWidth = 375;
    mockNavigator.mediaDevices.enumerateDevices.mockResolvedValue([
      { kind: 'videoinput', deviceId: 'camera1', label: 'Camera' }
    ]);
    mockNavigator.mediaDevices.getUserMedia.mockResolvedValue({
      getTracks: () => [{ stop: jest.fn() }]
    });

    const mode = await getRecommendedCameraMode();
    expect(mode).toBe('mobile');

    // Mock 桌面設備
    mockNavigator.userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)';
    mockWindow.innerWidth = 1920;

    const desktopMode = await getRecommendedCameraMode();
    expect(desktopMode).toBe('web');
  });
});

describe('相機策略', () => {
  test('應該創建Web相機策略', () => {
    const strategy = createCameraStrategy('web');
    expect(strategy).toBeDefined();
    expect(strategy.constructor.name).toBe('WebCameraStrategy');
  });

  test('應該創建移動端相機策略', () => {
    const strategy = createCameraStrategy('mobile');
    expect(strategy).toBeDefined();
    expect(strategy.constructor.name).toBe('MobileCameraStrategy');
  });

  test('應該拋出不支持模式的錯誤', () => {
    expect(() => {
      createCameraStrategy('unsupported');
    }).toThrow('不支持的相機模式: unsupported');
  });
});

describe('相機管理器', () => {
  let cameraManager;

  beforeEach(() => {
    cameraManager = getCameraManager();
    // 重置管理器狀態
    cameraManager.destroy();
  });

  test('應該獲取相機管理器實例', () => {
    expect(cameraManager).toBeDefined();
    expect(typeof cameraManager.initialize).toBe('function');
    expect(typeof cameraManager.startCamera).toBe('function');
    expect(typeof cameraManager.takePhoto).toBe('function');
    expect(typeof cameraManager.stopCamera).toBe('function');
  });

  test('應該正確初始化', async () => {
    // Mock 相機功能
    mockNavigator.mediaDevices.enumerateDevices.mockResolvedValue([
      { kind: 'videoinput', deviceId: 'camera1', label: 'Camera' }
    ]);
    mockNavigator.mediaDevices.getUserMedia.mockResolvedValue({
      getTracks: () => [{ stop: jest.fn() }]
    });

    await cameraManager.initialize();
    
    const status = cameraManager.getStatus();
    expect(status.isInitialized).toBe(true);
    expect(status.mode).toBeDefined();
  });

  test('應該處理初始化失敗', async () => {
    // Mock 無相機設備
    mockNavigator.mediaDevices.enumerateDevices.mockResolvedValue([]);

    await expect(cameraManager.initialize()).rejects.toThrow();
  });
});

describe('集成測試', () => {
  test('完整的拍照流程應該正常工作', async () => {
    // Mock 完整的相機環境
    mockNavigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)';
    mockWindow.innerWidth = 375;
    
    const mockStream = {
      getTracks: () => [{ stop: jest.fn() }]
    };
    
    mockNavigator.mediaDevices.enumerateDevices.mockResolvedValue([
      { kind: 'videoinput', deviceId: 'camera1', label: 'Camera' }
    ]);
    mockNavigator.mediaDevices.getUserMedia.mockResolvedValue(mockStream);

    const cameraManager = getCameraManager();
    
    // 初始化
    await cameraManager.initialize();
    expect(cameraManager.getStatus().isInitialized).toBe(true);
    
    // 檢查推薦模式
    expect(cameraManager.getMode()).toBe('mobile');
    
    // 清理
    cameraManager.destroy();
  });
});

// 測試輔助函數
export const createMockVideoElement = () => ({
  srcObject: null,
  videoWidth: 1280,
  videoHeight: 720,
  setAttribute: jest.fn(),
  muted: false
});

export const createMockCanvasElement = () => ({
  width: 0,
  height: 0,
  getContext: jest.fn(() => ({
    drawImage: jest.fn()
  })),
  toBlob: jest.fn((callback) => {
    const mockBlob = new Blob(['mock image data'], { type: 'image/jpeg' });
    callback(mockBlob);
  })
});

export const setupCameraMocks = () => {
  const mockVideo = createMockVideoElement();
  const mockCanvas = createMockCanvasElement();
  
  return { mockVideo, mockCanvas };
};
