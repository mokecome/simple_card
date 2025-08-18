# 環境自適應相機系統

## 概述

本系統實現了根據運行環境自動選擇最佳拍照模式的功能，為不同設備提供優化的用戶體驗。

## 系統架構

### 核心模塊

1. **環境檢測模塊** (`deviceDetector.js`)
   - 檢測設備類型（桌面/移動/平板）
   - 檢測瀏覽器環境
   - 檢測相機功能支持
   - 推薦最佳相機模式

2. **相機策略模塊** (`cameraStrategies.js`)
   - `WebCameraStrategy`: Web端Modal模式
   - `MobileCameraStrategy`: 移動端全屏模式
   - 統一的策略接口

3. **相機管理器** (`cameraManager.js`)
   - 統一的API接口
   - 自動策略選擇
   - 錯誤處理和降級

4. **移動端相機組件** (`MobileCameraModal.js`)
   - 全屏相機界面
   - 攝像頭切換功能
   - 優化的移動端體驗

## 功能特性

### 環境自適應
- **Web環境**: 使用Modal彈窗模式，適合桌面操作
- **移動端環境**: 使用全屏模式，提供沉浸式體驗
- **自動檢測**: 根據設備特徵自動選擇最佳模式

### 相機功能
- **多攝像頭支持**: 前置/後置攝像頭切換（移動端）
- **高質量拍照**: 根據設備優化圖片質量
- **權限處理**: 友好的權限請求和錯誤提示
- **設備兼容**: 支持各種設備和瀏覽器

### 用戶體驗
- **響應式設計**: 適配不同屏幕尺寸
- **直觀操作**: 簡潔的拍照界面
- **實時預覽**: 高質量的相機預覽
- **狀態反饋**: 清晰的操作狀態提示

## 使用方法

### 基本使用

```javascript
import { getCameraManager } from '../utils/cameraManager';

// 獲取相機管理器
const cameraManager = getCameraManager();

// 啟動相機
await cameraManager.startCamera('back', {
  videoElement: videoRef.current,
  canvasElement: canvasRef.current
});

// 拍照
const result = await cameraManager.takePhoto();

// 停止相機
cameraManager.stopCamera();
```

### 在React組件中使用

```javascript
import React, { useState, useEffect } from 'react';
import { getCameraManager } from '../utils/cameraManager';
import { getDeviceType } from '../utils/deviceDetector';
import MobileCameraModal from '../components/MobileCameraModal';

const CameraComponent = () => {
  const [cameraManager, setCameraManager] = useState(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const manager = getCameraManager();
    setCameraManager(manager);
    setIsMobile(getDeviceType() === 'mobile');
  }, []);

  const handleStartCamera = async () => {
    if (isMobile) {
      // 移動端使用全屏組件
      setShowMobileCamera(true);
    } else {
      // Web端使用傳統模式
      await cameraManager.startCamera('back');
    }
  };

  return (
    <div>
      <button onClick={handleStartCamera}>拍照</button>
      {isMobile && (
        <MobileCameraModal
          visible={showMobileCamera}
          onClose={() => setShowMobileCamera(false)}
          onPhotoTaken={handlePhotoTaken}
          cameraManager={cameraManager}
        />
      )}
    </div>
  );
};
```

## API 參考

### deviceDetector.js

```javascript
// 設備檢測
isMobileDevice() // 是否為移動設備
isWebBrowser()   // 是否為Web瀏覽器
getDeviceType()  // 獲取設備類型: 'mobile' | 'tablet' | 'desktop'

// 相機功能檢測
getCameraCapabilities()      // 獲取相機功能信息
getRecommendedCameraMode()   // 獲取推薦的相機模式
```

### cameraManager.js

```javascript
const manager = getCameraManager();

// 初始化
await manager.initialize();

// 相機控制
await manager.startCamera(target, options);
await manager.takePhoto();
manager.stopCamera();
await manager.switchCamera(); // 僅移動端

// 狀態查詢
manager.getStatus();
manager.getMode();
manager.supportsCameraSwitch();
```

### 事件回調

```javascript
cameraManager.setCallbacks({
  cameraStart: (data) => console.log('相機啟動', data),
  cameraStop: () => console.log('相機停止'),
  cameraError: (error) => console.error('相機錯誤', error),
  photoTaken: (data) => console.log('拍照完成', data),
  cameraSwitch: (data) => console.log('攝像頭切換', data)
});
```

## 配置選項

### 相機約束

```javascript
const constraints = {
  video: {
    facingMode: 'environment', // 'user' | 'environment'
    width: { ideal: 1920 },
    height: { ideal: 1080 }
  }
};

await cameraManager.startCamera('back', { constraints });
```

### 移動端組件屬性

```javascript
<MobileCameraModal
  visible={true}
  onClose={handleClose}
  onPhotoTaken={handlePhotoTaken}
  cameraManager={cameraManager}
  target="back" // 'front' | 'back'
/>
```

## 錯誤處理

系統提供完善的錯誤處理機制：

- **權限錯誤**: 相機權限被拒絕
- **設備錯誤**: 未找到相機設備
- **占用錯誤**: 相機被其他應用占用
- **約束錯誤**: 不支持的相機約束
- **網絡錯誤**: 網絡連接問題

## 瀏覽器兼容性

- **Chrome**: 完全支持
- **Firefox**: 完全支持
- **Safari**: 支持（iOS需要HTTPS）
- **Edge**: 完全支持
- **移動瀏覽器**: 優化支持

## 性能優化

- **懶加載**: 按需加載相機模塊
- **資源管理**: 及時釋放相機資源
- **圖片優化**: 根據設備調整圖片質量
- **內存管理**: 避免內存洩漏

## 測試

運行測試：

```bash
npm test -- cameraSystem.test.js
```

測試覆蓋：
- 設備檢測功能
- 相機功能檢測
- 策略創建和切換
- 管理器初始化和控制
- 集成測試

## 故障排除

### 常見問題

1. **相機無法啟動**
   - 檢查瀏覽器權限設置
   - 確保使用HTTPS（移動端必需）
   - 檢查設備是否有可用相機

2. **移動端全屏不工作**
   - 檢查CSS樣式是否正確加載
   - 確保組件正確渲染

3. **攝像頭切換失敗**
   - 檢查設備是否支持多攝像頭
   - 確認瀏覽器支持facingMode約束

### 調試模式

啟用詳細日誌：

```javascript
// 在瀏覽器控制台中設置
localStorage.setItem('camera-debug', 'true');
```

## 更新日誌

### v1.0.0
- 初始版本發布
- 支持Web和移動端自適應
- 實現基本的拍照功能
- 添加攝像頭切換支持
