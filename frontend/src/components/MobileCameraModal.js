/**
 * 移動端全屏相機組件
 * 提供優化的移動端拍照體驗
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Button } from 'antd-mobile';
import {
  CameraOutline,
  CloseOutline,
  RedoOutline,
  CheckOutline,
  LoopOutline
} from 'antd-mobile-icons';
import './MobileCameraModal.css';

const MobileCameraModal = ({ 
  visible, 
  onClose, 
  onPhotoTaken, 
  cameraManager,
  target = 'back'
}) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isReady, setIsReady] = useState(false);
  const [supportsCameraSwitch, setSupportsCameraSwitch] = useState(false);
  const [currentFacingMode, setCurrentFacingMode] = useState('environment');
  const [isCapturing, setIsCapturing] = useState(false);
  const [showGrid, setShowGrid] = useState(false);
  const [focusPoint, setFocusPoint] = useState(null);

  // 相機啟動成功回調
  const handleCameraStart = useCallback((data) => {
    setIsReady(true);
    if (data.facingMode) {
      setCurrentFacingMode(data.facingMode);
    }
  }, []);

  // 相機錯誤回調
  const handleCameraError = useCallback((error) => {
    console.error('相機錯誤:', error);
    setIsReady(false);
  }, []);

  // 攝像頭切換回調
  const handleCameraSwitch = useCallback((data) => {
    if (data.facingMode) {
      setCurrentFacingMode(data.facingMode);
    }
  }, []);

  // 關閉相機
  const handleClose = useCallback(() => {
    if (cameraManager) {
      cameraManager.stopCamera();
    }
    setIsReady(false);
    setIsCapturing(false);
    setFocusPoint(null);
    if (onClose) {
      onClose();
    }
  }, [cameraManager, onClose]);

  // 拍照完成回調
  const handlePhotoTaken = useCallback((data) => {
    setIsCapturing(false);
    if (onPhotoTaken) {
      onPhotoTaken(data);
    }
    handleClose();
  }, [onPhotoTaken, handleClose]);

  // 手動對焦功能
  const handleFocus = useCallback((event) => {
    if (!isReady || !videoRef.current) return;

    // 獲取點擊位置
    const rect = videoRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // 計算相對位置
    const relativeX = (x / rect.width) * 100;
    const relativeY = (y / rect.height) * 100;

    console.log('手動對焦位置:', { x: relativeX, y: relativeY });

    // 顯示對焦指示器
    setFocusPoint({ x: relativeX, y: relativeY });

    // 嘗試調用瀏覽器對焦API（如果支持）
    try {
      const videoTrack = videoRef.current.srcObject?.getVideoTracks()[0];
      if (videoTrack && videoTrack.getCapabilities) {
        const capabilities = videoTrack.getCapabilities();
        if (capabilities.focusMode) {
          // 設置對焦模式為手動或連續
          videoTrack.applyConstraints({
            advanced: [{
              focusMode: 'continuous',
              pointsOfInterest: [{ x: relativeX / 100, y: relativeY / 100 }]
            }]
          }).catch(err => {
            console.log('對焦約束設置失敗:', err);
          });
        }
      }
    } catch (error) {
      console.log('對焦功能不支持:', error);
    }

    // 清除對焦指示器
    setTimeout(() => {
      setFocusPoint(null);
    }, 1500);
  }, [isReady]);

  // 切換網格線
  const toggleGrid = useCallback(() => {
    setShowGrid(prev => !prev);
  }, []);

  // 初始化相機
  const initializeCamera = useCallback(async () => {
    try {
      setIsReady(false);

      console.log('移動端相機初始化開始...', {
        target,
        videoElement: !!videoRef.current,
        canvasElement: !!canvasRef.current
      });

      // 設置相機管理器回調
      cameraManager.setCallbacks({
        cameraStart: handleCameraStart,
        cameraError: handleCameraError,
        cameraSwitch: handleCameraSwitch,
        photoTaken: handlePhotoTaken
      });

      // 等待DOM元素準備就緒
      if (!videoRef.current || !canvasRef.current) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // 啟動相機
      await cameraManager.startCamera(target, {
        videoElement: videoRef.current,
        canvasElement: canvasRef.current
      });

      // 檢查是否支持攝像頭切換
      setSupportsCameraSwitch(cameraManager.supportsCameraSwitch());

      console.log('移動端相機初始化完成');

    } catch (error) {
      console.error('初始化相機失敗:', error);
      handleCameraError(error);
    }
  }, [cameraManager, target, handleCameraStart, handleCameraError, handleCameraSwitch, handlePhotoTaken]);

  // 初始化相機
  useEffect(() => {
    if (visible && cameraManager) {
      initializeCamera();
    }

    return () => {
      if (cameraManager) {
        cameraManager.stopCamera();
      }
    };
  }, [visible, cameraManager, target, initializeCamera]);

  // 拍照
  const handleTakePhoto = useCallback(async () => {
    if (!isReady || isCapturing) {
      console.log('拍照條件不滿足', { isReady, isCapturing });
      return;
    }

    if (!cameraManager) {
      console.error('相機管理器未初始化');
      return;
    }

    try {
      setIsCapturing(true);
      console.log('移動端開始拍照...');

      // 拍照前短暫延遲，確保對焦穩定
      await new Promise(resolve => setTimeout(resolve, 200));

      const result = await cameraManager.takePhoto();

      if (result && result.file) {
        console.log('移動端拍照成功', {
          fileSize: result.file.size,
          facingMode: result.facingMode
        });
      }
    } catch (error) {
      console.error('移動端拍照失敗:', error);
      setIsCapturing(false);
    }
  }, [isReady, isCapturing, cameraManager]);

  // 切換攝像頭
  const handleSwitchCamera = useCallback(async () => {
    if (!supportsCameraSwitch) return;

    try {
      await cameraManager.switchCamera();
    } catch (error) {
      console.error('切換攝像頭失敗:', error);
    }
  }, [supportsCameraSwitch, cameraManager]);

  if (!visible) {
    return null;
  }

  return (
    <div className="mobile-camera-modal">
      <div className="camera-container">
        {/* 視頻預覽 */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="camera-video"
          onClick={handleFocus}
        />
        
        {/* 網格線輔助 */}
        <div className={`camera-grid ${!showGrid ? 'hidden' : ''}`}></div>
        
        {/* 隱藏的畫布用於拍照 */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        
        {/* 對焦指示器 */}
        {focusPoint && (
          <div 
            className="focus-indicator active"
            style={{
              left: `${focusPoint.x}%`,
              top: `${focusPoint.y}%`
            }}
          />
        )}
        
        {/* 相機未準備就緒時的加載提示 */}
        {!isReady && (
          <div className="camera-loading">
            <div className="loading-spinner"></div>
            {/* 移除加載文字，只保留視覺指示器 */}
          </div>
        )}
        
        {/* 拍照指引線 - 更新版本 */}
        {isReady && (
          <div className="camera-guides">
            <div className="guide-corner top-left"></div>
            <div className="guide-corner top-right"></div>
            <div className="guide-corner bottom-left"></div>
            <div className="guide-corner bottom-right"></div>

            {/* 拍攝範圍提示 */}
            <div className="capture-hint">
              <div className="hint-text">高清拍攝區域</div>
              <div className="hint-subtext">將文件對準此區域以獲得最佳OCR效果</div>
            </div>
          </div>
        )}
        
        {/* 控制按鈕 */}
        <div className="camera-controls">
          <div className="controls-top">
            <Button
              color="primary"
              fill="none"
              onClick={handleClose}
              className="control-button close-button"
            >
              <CloseOutline />
            </Button>
            
            <div style={{ display: 'flex', gap: '12px' }}>
              <Button
                color="primary"
                fill="none"
                onClick={toggleGrid}
                className="control-button grid-button"
                disabled={!isReady}
              >
                <LoopOutline />
              </Button>
              
              {supportsCameraSwitch && (
                <Button
                  color="primary"
                  fill="none"
                  onClick={handleSwitchCamera}
                  className="control-button switch-button"
                  disabled={!isReady}
                >
                  <RedoOutline />
                </Button>
              )}
            </div>
          </div>
          
          <div className="controls-bottom">
            <div className="capture-area">
              <Button
                color="primary"
                size="large"
                onClick={handleTakePhoto}
                disabled={!isReady || isCapturing}
                className="capture-button"
                loading={isCapturing}
              >
                {isCapturing ? <CheckOutline /> : <CameraOutline />}
              </Button>
            </div>
            
            {/* 移除攝像頭狀態指示文字，減少視覺干擾 */}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MobileCameraModal;
