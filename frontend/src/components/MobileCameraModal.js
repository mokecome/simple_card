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
  AppstoreOutline
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

  // 快取 video 尺寸（拍照前記錄，避免 callback 時 video 已被關閉）
  const cachedVideoDims = useRef(null);

  // 計算提示框對應的 video 原生像素裁切區域
  // video 使用 object-fit:cover，需要從 CSS % 反算回原生座標
  const computeGuideFrameRect = useCallback((useCached = false) => {
    let videoW, videoH, containerW, containerH;

    if (useCached && cachedVideoDims.current) {
      ({ videoW, videoH, containerW, containerH } = cachedVideoDims.current);
    } else {
      const video = videoRef.current;
      if (!video) return null;
      videoW = video.videoWidth;
      videoH = video.videoHeight;
      containerW = video.clientWidth;
      containerH = video.clientHeight;
    }

    if (!videoW || !videoH || !containerW || !containerH) return null;

    // --- 取得當前提示框 CSS 百分比（與 MobileCameraModal.css 同步） ---
    const screenWidth = window.innerWidth;
    const isLandscape = window.matchMedia('(orientation: landscape)').matches;

    let guideTop, guideBottom, guideLeft, guideRight;
    if (isLandscape) {
      guideTop = 0.15; guideBottom = 0.20; guideLeft = 0.15; guideRight = 0.15;
    } else if (screenWidth <= 480) {
      guideTop = 0.25; guideBottom = 0.30; guideLeft = 0.04; guideRight = 0.04;
    } else {
      guideTop = 0.28; guideBottom = 0.33; guideLeft = 0.05; guideRight = 0.05;
    }

    // --- object-fit:cover 映射 ---
    const videoRatio = videoW / videoH;
    const containerRatio = containerW / containerH;

    let scale, offsetX, offsetY;
    if (videoRatio > containerRatio) {
      // video 比容器寬 → 左右被裁
      scale = containerH / videoH;
      offsetX = (videoW * scale - containerW) / 2;
      offsetY = 0;
    } else {
      // video 比容器高 → 上下被裁
      scale = containerW / videoW;
      offsetX = 0;
      offsetY = (videoH * scale - containerH) / 2;
    }

    // 提示框在容器中的像素位置
    const frameLeft   = guideLeft * containerW;
    const frameTop    = guideTop * containerH;
    const frameRight  = (1 - guideRight) * containerW;
    const frameBottom = (1 - guideBottom) * containerH;

    // 反算回 video 原生像素座標
    const natLeft   = Math.max(0, Math.round((frameLeft + offsetX) / scale));
    const natTop    = Math.max(0, Math.round((frameTop + offsetY) / scale));
    const natRight  = Math.min(videoW, Math.round((frameRight + offsetX) / scale));
    const natBottom = Math.min(videoH, Math.round((frameBottom + offsetY) / scale));

    return { x: natLeft, y: natTop, width: natRight - natLeft, height: natBottom - natTop };
  }, []);

  // 拍照完成回調
  const handlePhotoTaken = useCallback((data) => {
    // 使用快取的 video 尺寸計算提示框裁切區域（拍照後 video 可能已被關閉）
    const guideFrameRect = computeGuideFrameRect(true);

    setIsCapturing(false);

    if (onPhotoTaken) {
      onPhotoTaken({ ...data, guideFrameRect });
    }
    handleClose();
  }, [onPhotoTaken, handleClose, computeGuideFrameRect]);

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

      // 拍照前先快取 video 尺寸（拍照後 video 可能已被關閉，尺寸歸零）
      const video = videoRef.current;
      if (video) {
        cachedVideoDims.current = {
          videoW: video.videoWidth,
          videoH: video.videoHeight,
          containerW: video.clientWidth,
          containerH: video.clientHeight,
        };
      }

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
        
        {/* 暗色遮罩 + 名片框指引 */}
        {isReady && (
          <>
            <div className="camera-overlay">
              <div className="overlay-top"></div>
              <div className="overlay-bottom"></div>
              <div className="overlay-left"></div>
              <div className="overlay-right"></div>
            </div>
            <div className="card-window">
              <div className="corner-accent top-left"></div>
              <div className="corner-accent top-right"></div>
              <div className="corner-accent bottom-left"></div>
              <div className="corner-accent bottom-right"></div>
              <div className="scan-line"></div>
            </div>
            <div className="card-hint">將名片放入框內拍攝</div>
          </>
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
                <AppstoreOutline />
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
