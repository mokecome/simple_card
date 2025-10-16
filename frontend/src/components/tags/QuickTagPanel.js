import React, { useState, useEffect } from 'react';
import { Tag, Button, Input, Space, Divider, Toast } from 'antd-mobile';
import { AddOutline, CloseOutline } from 'antd-mobile-icons';
import './QuickTagPanel.css';

/**
 * 快速標籤面板組件
 * 在名片創建/掃描後立即彈出，提供3秒內快速打標功能
 *
 * 設計原則：
 * 1. 用戶標籤優先 - 用戶自定義標籤為主
 * 2. 快速操作 - 3秒內完成標籤選擇
 * 3. 智能建議 - 系統根據公司名稱推薦標籤
 */
const QuickTagPanel = ({
  visible,
  cardId,
  cardData = {},
  onClose,
  onTagsAdded
}) => {
  const [selectedTags, setSelectedTags] = useState([]);
  const [customTag, setCustomTag] = useState('');
  const [suggestedTags, setSuggestedTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [allTags, setAllTags] = useState([]);

  // 預設標籤 - 根據用戶常用場景設計（5-7個）
  const presetTags = [
    '重要客戶',
    '潛在客戶',
    '合作夥伴',
    '供應商',
    '待跟進',
    '已成交',
    '技術顧問'
  ];

  // 載入所有現有標籤用於自動完成
  useEffect(() => {
    if (visible) {
      fetchAllTags();
      generateSuggestedTags();
    }
  }, [visible, cardData]);

  const fetchAllTags = async () => {
    try {
      const response = await fetch('/api/v1/cards/tags/list');
      const result = await response.json();

      if (result.success && result.data) {
        // 只取用戶標籤，按使用次數排序
        const userTags = result.data
          .filter(tag => tag.tag_type === 'user')
          .sort((a, b) => b.count - a.count)
          .map(tag => tag.tag_name);
        setAllTags(userTags);
      }
    } catch (error) {
      console.error('載入標籤列表失敗:', error);
    }
  };

  // 根據名片數據生成系統推薦標籤
  const generateSuggestedTags = () => {
    const suggestions = [];
    const companyName = cardData.company_name_zh || cardData.company_name_en || '';
    const position = cardData.position_zh || cardData.position_en || '';

    // 根據公司名稱推薦行業標籤
    if (companyName) {
      if (companyName.includes('科技') || companyName.includes('Tech')) {
        suggestions.push('科技業');
      }
      if (companyName.includes('金融') || companyName.includes('銀行') || companyName.includes('Bank')) {
        suggestions.push('金融業');
      }
      if (companyName.includes('醫療') || companyName.includes('Health')) {
        suggestions.push('醫療業');
      }
      if (companyName.includes('製造') || companyName.includes('Manufacturing')) {
        suggestions.push('製造業');
      }
    }

    // 根據職位推薦職級標籤
    if (position) {
      if (position.includes('總經理') || position.includes('CEO') || position.includes('總裁')) {
        suggestions.push('高階主管');
      } else if (position.includes('經理') || position.includes('Manager')) {
        suggestions.push('中階主管');
      } else if (position.includes('工程師') || position.includes('Engineer')) {
        suggestions.push('技術人員');
      }
    }

    setSuggestedTags(suggestions.slice(0, 3)); // 最多3個建議
  };

  const handleTagSelect = (tag) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter(t => t !== tag));
    } else {
      if (selectedTags.length < 10) {
        setSelectedTags([...selectedTags, tag]);
      } else {
        Toast.show({
          content: '最多只能選擇10個標籤',
          position: 'center',
        });
      }
    }
  };

  const handleAddCustomTag = () => {
    const trimmedTag = customTag.trim();
    if (!trimmedTag) {
      return;
    }

    if (trimmedTag.length > 50) {
      Toast.show({
        content: '標籤名稱不能超過50個字符',
        position: 'center',
      });
      return;
    }

    if (selectedTags.includes(trimmedTag)) {
      Toast.show({
        content: '標籤已存在',
        position: 'center',
      });
      return;
    }

    if (selectedTags.length >= 10) {
      Toast.show({
        content: '最多只能選擇10個標籤',
        position: 'center',
      });
      return;
    }

    setSelectedTags([...selectedTags, trimmedTag]);
    setCustomTag('');
  };

  const handleSave = async () => {
    if (selectedTags.length === 0) {
      // 允許不打標直接關閉
      onClose();
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`/api/v1/cards/${cardId}/tags`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tags: selectedTags,
          tag_type: 'user'
        })
      });

      const result = await response.json();

      if (result.success) {
        Toast.show({
          content: result.message || '標籤添加成功',
          position: 'center',
        });
        if (onTagsAdded) {
          onTagsAdded(selectedTags);
        }
        onClose();
      } else {
        Toast.show({
          content: result.message || '標籤添加失敗',
          position: 'center',
        });
      }
    } catch (error) {
      console.error('保存標籤失敗:', error);
      Toast.show({
        content: '保存標籤失敗',
        position: 'center',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  if (!visible) return null;

  return (
    <div className="quick-tag-panel-overlay">
      <div className="quick-tag-panel">
        <div className="panel-header">
          <h3>快速打標</h3>
          <CloseOutline onClick={handleSkip} className="close-icon" />
        </div>

        <Divider style={{ margin: '12px 0' }} />

        {/* 已選標籤 */}
        <div className="selected-tags-section">
          <div className="section-title">已選標籤 ({selectedTags.length}/10)</div>
          <div className="tags-container">
            {selectedTags.length === 0 ? (
              <span className="empty-hint">點擊下方標籤或輸入自定義標籤</span>
            ) : (
              selectedTags.map(tag => (
                <Tag
                  key={tag}
                  closable
                  onClose={() => handleTagSelect(tag)}
                  color="blue"
                >
                  {tag}
                </Tag>
              ))
            )}
          </div>
        </div>

        {/* 智能推薦 */}
        {suggestedTags.length > 0 && (
          <div className="suggested-tags-section">
            <div className="section-title">智能推薦</div>
            <div className="tags-container">
              {suggestedTags.map(tag => (
                <Tag
                  key={tag}
                  onClick={() => handleTagSelect(tag)}
                  color={selectedTags.includes(tag) ? 'blue' : 'default'}
                  style={{ cursor: 'pointer' }}
                >
                  {tag}
                </Tag>
              ))}
            </div>
          </div>
        )}

        {/* 預設標籤 */}
        <div className="preset-tags-section">
          <div className="section-title">常用標籤</div>
          <div className="tags-container">
            {presetTags.map(tag => (
              <Tag
                key={tag}
                onClick={() => handleTagSelect(tag)}
                color={selectedTags.includes(tag) ? 'blue' : 'default'}
                style={{ cursor: 'pointer' }}
              >
                {tag}
              </Tag>
            ))}
          </div>
        </div>

        {/* 自定義標籤輸入 */}
        <div className="custom-tag-section">
          <div className="section-title">自定義標籤</div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Input
              placeholder="輸入自定義標籤（最多50字）"
              value={customTag}
              onChange={(val) => setCustomTag(val)}
              onEnterPress={handleAddCustomTag}
              maxLength={50}
              style={{ flex: 1 }}
            />
            <Button
              color="primary"
              onClick={handleAddCustomTag}
            >
              <AddOutline /> 添加
            </Button>
          </div>
        </div>

        {/* 操作按鈕 */}
        <div className="panel-actions">
          <Button onClick={handleSkip} style={{ marginRight: '8px' }}>
            跳過
          </Button>
          <Button
            color="primary"
            onClick={handleSave}
            loading={loading}
          >
            保存標籤 ({selectedTags.length})
          </Button>
        </div>
      </div>
    </div>
  );
};

export default QuickTagPanel;
