import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Modal, Button, Space } from 'antd-mobile';

const CardCropEditor = ({
  visible,
  imageSrc,
  initialCorners,
  onCancel,
  onConfirm,
}) => {
  const imageRef = useRef(null);
  const containerRef = useRef(null);
  // cropRect: [x1, y1, x2, y2] in display pixels (top-left, bottom-right)
  const [cropRect, setCropRect] = useState([40, 40, 260, 160]);
  const [dragging, setDragging] = useState(null); // { type: 'corner'|'edge', id: 0-3|'top'|'bottom'|'left'|'right' }
  const [imageSize, setImageSize] = useState({
    naturalWidth: 0,
    naturalHeight: 0,
    clientWidth: 0,
    clientHeight: 0,
  });

  const handleImageLoad = () => {
    const img = imageRef.current;
    if (!img) return;

    // 計算 objectFit: contain 下圖片實際渲染的尺寸和偏移
    const natW = img.naturalWidth;
    const natH = img.naturalHeight;
    const elemW = img.clientWidth;
    const elemH = img.clientHeight;

    const imgRatio = natW / natH;
    const elemRatio = elemW / elemH;

    let renderW, renderH, offsetX, offsetY;
    if (imgRatio > elemRatio) {
      // 圖片較寬，寬度撐滿，高度有留白
      renderW = elemW;
      renderH = elemW / imgRatio;
      offsetX = 0;
      offsetY = (elemH - renderH) / 2;
    } else {
      // 圖片較高，高度撐滿，寬度有留白
      renderH = elemH;
      renderW = elemH * imgRatio;
      offsetX = (elemW - renderW) / 2;
      offsetY = 0;
    }

    setImageSize({
      naturalWidth: natW,
      naturalHeight: natH,
      clientWidth: elemW,
      clientHeight: elemH,
      renderWidth: renderW,
      renderHeight: renderH,
      offsetX: offsetX,
      offsetY: offsetY,
    });
  };

  const createDefaultRect = (width, height) => {
    if (!width || !height) return [40, 40, 260, 160];
    const marginX = width * 0.12;
    const marginY = height * 0.18;
    return [marginX, marginY, width - marginX, height - marginY];
  };

  // Convert 4-corner natural coords to display rect [x1,y1,x2,y2]
  const cornersToDisplayRect = (corners) => {
    const rw = imageSize.renderWidth;
    const rh = imageSize.renderHeight;
    const ox = imageSize.offsetX || 0;
    const oy = imageSize.offsetY || 0;
    if (
      !corners || corners.length !== 4 ||
      !imageSize.naturalWidth || !imageSize.naturalHeight || !rw || !rh
    ) {
      return createDefaultRect(rw || imageSize.clientWidth, rh || imageSize.clientHeight);
    }
    const scaleX = rw / imageSize.naturalWidth;
    const scaleY = rh / imageSize.naturalHeight;
    const xs = corners.map(c => c[0] * scaleX + ox);
    const ys = corners.map(c => c[1] * scaleY + oy);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  };

  // Convert display rect [x1,y1,x2,y2] to 4-corner natural coords (TL, TR, BR, BL)
  const rectToNaturalCorners = (rect) => {
    const rw = imageSize.renderWidth;
    const rh = imageSize.renderHeight;
    const ox = imageSize.offsetX || 0;
    const oy = imageSize.offsetY || 0;
    if (
      !imageSize.naturalWidth || !imageSize.naturalHeight || !rw || !rh
    ) {
      const [x1, y1, x2, y2] = rect;
      return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]];
    }
    const scaleX = imageSize.naturalWidth / rw;
    const scaleY = imageSize.naturalHeight / rh;
    const [x1, y1, x2, y2] = rect;
    return [
      [Math.round((x1 - ox) * scaleX), Math.round((y1 - oy) * scaleY)],
      [Math.round((x2 - ox) * scaleX), Math.round((y1 - oy) * scaleY)],
      [Math.round((x2 - ox) * scaleX), Math.round((y2 - oy) * scaleY)],
      [Math.round((x1 - ox) * scaleX), Math.round((y2 - oy) * scaleY)],
    ];
  };

  useEffect(() => {
    if (!visible) return;
    if (!imageSize.clientWidth || !imageSize.clientHeight) return;

    if (initialCorners && initialCorners.length === 4) {
      setCropRect(cornersToDisplayRect(initialCorners));
    } else {
      setCropRect(createDefaultRect(imageSize.clientWidth, imageSize.clientHeight));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, imageSize]);

  const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

  const handlePointerMove = useCallback((event) => {
    if (!dragging) return;
    event.preventDefault();

    const container = containerRef.current;
    if (!container) return;

    const touch = event.touches && event.touches.length > 0 ? event.touches[0] : event;
    const containerRect = container.getBoundingClientRect();
    const ox = imageSize.offsetX || 0;
    const oy = imageSize.offsetY || 0;
    const rw = imageSize.renderWidth || imageSize.clientWidth;
    const rh = imageSize.renderHeight || imageSize.clientHeight;
    const px = clamp(touch.clientX - containerRect.left, ox, ox + rw);
    const py = clamp(touch.clientY - containerRect.top, oy, oy + rh);

    setCropRect(prev => {
      const next = [...prev];
      if (dragging.type === 'corner') {
        // 0=TL, 1=TR, 2=BR, 3=BL — opposite corner stays fixed
        if (dragging.id === 0) { next[0] = px; next[1] = py; }
        else if (dragging.id === 1) { next[2] = px; next[1] = py; }
        else if (dragging.id === 2) { next[2] = px; next[3] = py; }
        else if (dragging.id === 3) { next[0] = px; next[3] = py; }
      } else if (dragging.type === 'edge') {
        if (dragging.id === 'top') next[1] = py;
        else if (dragging.id === 'bottom') next[3] = py;
        else if (dragging.id === 'left') next[0] = px;
        else if (dragging.id === 'right') next[2] = px;
      }
      return next;
    });
  }, [dragging, imageSize]);

  const handlePointerUp = useCallback(() => {
    if (dragging) {
      // Normalize: ensure x1<x2, y1<y2
      setCropRect(prev => {
        const [x1, y1, x2, y2] = prev;
        return [Math.min(x1, x2), Math.min(y1, y2), Math.max(x1, x2), Math.max(y1, y2)];
      });
      setDragging(null);
    }
  }, [dragging]);

  const startDragging = (type, id, event) => {
    event.preventDefault();
    setDragging({ type, id });
  };

  useEffect(() => {
    if (!dragging) return;

    window.addEventListener('mousemove', handlePointerMove);
    window.addEventListener('mouseup', handlePointerUp);
    window.addEventListener('touchmove', handlePointerMove, { passive: false });
    window.addEventListener('touchend', handlePointerUp);

    return () => {
      window.removeEventListener('mousemove', handlePointerMove);
      window.removeEventListener('mouseup', handlePointerUp);
      window.removeEventListener('touchmove', handlePointerMove);
      window.removeEventListener('touchend', handlePointerUp);
    };
  }, [dragging, handlePointerMove, handlePointerUp]);

  // Derived rect values (always normalized)
  const left = Math.min(cropRect[0], cropRect[2]);
  const top = Math.min(cropRect[1], cropRect[3]);
  const right = Math.max(cropRect[0], cropRect[2]);
  const bottom = Math.max(cropRect[1], cropRect[3]);
  const rectW = right - left;
  const rectH = bottom - top;

  const cornerPositions = [
    [left, top],     // 0: TL
    [right, top],    // 1: TR
    [right, bottom], // 2: BR
    [left, bottom],  // 3: BL
  ];

  const overlayStyle = {
    position: 'absolute',
    background: 'rgba(0, 0, 0, 0.55)',
    pointerEvents: 'none',
    zIndex: 3,
  };

  return (
    <Modal
      visible={visible}
      destroyOnClose
      content={
        <div style={{ padding: '8px' }}>
          <div
            ref={containerRef}
            style={{
              position: 'relative',
              width: '100%',
              maxWidth: '100%',
              margin: '0 auto',
              touchAction: 'none',
            }}
          >
            <img
              ref={imageRef}
              src={imageSrc}
              alt="crop editor"
              onLoad={handleImageLoad}
              style={{
                width: '100%',
                maxHeight: '55vh',
                objectFit: 'contain',
                display: 'block',
                borderRadius: '8px',
              }}
            />

            {/* Dark overlay masks (top, bottom, left, right) */}
            <div style={{ ...overlayStyle, left: 0, top: 0, width: imageSize.clientWidth, height: top }} />
            <div style={{ ...overlayStyle, left: 0, top: bottom, width: imageSize.clientWidth, height: imageSize.clientHeight - bottom }} />
            <div style={{ ...overlayStyle, left: 0, top: top, width: left, height: rectH }} />
            <div style={{ ...overlayStyle, left: right, top: top, width: imageSize.clientWidth - right, height: rectH }} />

            {/* Crop rect border */}
            <div
              style={{
                position: 'absolute',
                left, top, width: rectW, height: rectH,
                border: '2px solid rgba(255,255,255,0.85)',
                borderRadius: '2px',
                pointerEvents: 'none',
                zIndex: 4,
                boxShadow: '0 0 0 1px rgba(0,0,0,0.3)',
              }}
            />

            {/* Edge handles */}
            {/* Top edge */}
            <div
              onMouseDown={(e) => startDragging('edge', 'top', e)}
              onTouchStart={(e) => startDragging('edge', 'top', e)}
              style={{ position: 'absolute', left, top: top, width: rectW, height: 20, transform: 'translateY(-50%)', cursor: 'ns-resize', zIndex: 5, touchAction: 'none', background: 'transparent' }}
            />
            {/* Bottom edge */}
            <div
              onMouseDown={(e) => startDragging('edge', 'bottom', e)}
              onTouchStart={(e) => startDragging('edge', 'bottom', e)}
              style={{ position: 'absolute', left, top: bottom, width: rectW, height: 20, transform: 'translateY(-50%)', cursor: 'ns-resize', zIndex: 5, touchAction: 'none', background: 'transparent' }}
            />
            {/* Left edge */}
            <div
              onMouseDown={(e) => startDragging('edge', 'left', e)}
              onTouchStart={(e) => startDragging('edge', 'left', e)}
              style={{ position: 'absolute', left: left, top: top, width: 20, height: rectH, transform: 'translateX(-50%)', cursor: 'ew-resize', zIndex: 5, touchAction: 'none', background: 'transparent' }}
            />
            {/* Right edge */}
            <div
              onMouseDown={(e) => startDragging('edge', 'right', e)}
              onTouchStart={(e) => startDragging('edge', 'right', e)}
              style={{ position: 'absolute', left: right, top: top, width: 20, height: rectH, transform: 'translateX(-50%)', cursor: 'ew-resize', zIndex: 5, touchAction: 'none', background: 'transparent' }}
            />

            {/* Corner handles */}
            {cornerPositions.map((pos, index) => (
              <div
                key={index}
                onMouseDown={(e) => startDragging('corner', index, e)}
                onTouchStart={(e) => startDragging('corner', index, e)}
                style={{
                  position: 'absolute',
                  left: `${pos[0]}px`,
                  top: `${pos[1]}px`,
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  background: dragging && dragging.type === 'corner' && dragging.id === index ? '#ff7a00' : '#1677ff',
                  border: '2px solid #fff',
                  transform: 'translate(-50%, -50%)',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.25)',
                  cursor: 'grab',
                  touchAction: 'none',
                  zIndex: 10,
                }}
              />
            ))}
          </div>

          <div style={{ display: 'flex', gap: '8px', marginTop: '12px', justifyContent: 'flex-end' }}>
            <Button onClick={onCancel}>取消</Button>
            <Button
              color="primary"
              onClick={() => onConfirm(rectToNaturalCorners(cropRect))}
            >
              確認裁切
            </Button>
          </div>
        </div>
      }
      onClose={onCancel}
    />
  );
};

export default CardCropEditor;
