import React from 'react';
import { Loading } from 'antd-mobile';

/**
 * 統一的加載動畫組件
 * @param {Object} props
 * @param {boolean} props.visible - 是否顯示
 * @param {string} props.text - 加載文字
 * @param {string} props.size - 尺寸：'small', 'medium', 'large'
 */
const LoadingSpinner = ({ 
  visible = false, 
  text = '載入中...', 
  size = 'medium' 
}) => {
  if (!visible) return null;

  const getSizeStyle = () => {
    switch (size) {
      case 'small':
        return { padding: '20px' };
      case 'large':
        return { padding: '60px' };
      case 'medium':
      default:
        return { padding: '40px' };
    }
  };

  return (
    <div 
      style={{ 
        textAlign: 'center', 
        ...getSizeStyle() 
      }}
    >
      <Loading />
      {text && (
        <div style={{ 
          marginTop: '12px', 
          color: '#666', 
          fontSize: '14px' 
        }}>
          {text}
        </div>
      )}
    </div>
  );
};

export default LoadingSpinner;