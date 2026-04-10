import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Checkbox, Dialog, Toast, NavBar, SpinLoading, ImageViewer } from 'antd-mobile';
import { LeftOutline, RightOutline, EyeOutline } from 'antd-mobile-icons';
import axios from 'axios';
import './DuplicateComparePage.css';

function getImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('card_data/')) return `/static/${path}`;
  if (path.startsWith('output/card_images/')) {
    return `/static/uploads/${path.replace('output/card_images/', '')}`;
  }
  return path;
}

export default function DuplicateComparePage() {
  const navigate = useNavigate();
  const { groupId } = useParams();

  const [loading, setLoading] = useState(true);
  const [groups, setGroups] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [totalGroups, setTotalGroups] = useState(0);
  const [selectedForDelete, setSelectedForDelete] = useState(new Set());
  const [deleting, setDeleting] = useState(false);

  const loadGroupByIndex = useCallback(async (index) => {
    setLoading(true);
    setSelectedForDelete(new Set());
    try {
      const res = await axios.get('/api/v1/cards/duplicates', {
        params: { skip: index, limit: 1 }
      });
      const resData = res.data;
      if (resData?.success && resData.data) {
        setGroups(resData.data.groups || []);
        setTotalGroups(resData.data.total_groups || 0);
        setCurrentIndex(resData.data.current_index ?? index);
      }
    } catch (err) {
      Toast.show({ content: '載入失敗', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadGroupById = useCallback(async (gid) => {
    setLoading(true);
    setSelectedForDelete(new Set());
    try {
      const res = await axios.get('/api/v1/cards/duplicates', {
        params: { group_id: gid }
      });
      const resData = res.data;
      if (resData?.success && resData.data) {
        setGroups(resData.data.groups || []);
        setTotalGroups(resData.data.total_groups || 0);
        setCurrentIndex(resData.data.current_index ?? 0);
      }
    } catch (err) {
      Toast.show({ content: '載入失敗', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (groupId && groupId !== 'all') {
      loadGroupById(groupId);
    } else {
      loadGroupByIndex(0);
    }
  }, [groupId, loadGroupById, loadGroupByIndex]);

  const currentGroup = groups[0];

  const toggleSelect = (cardId) => {
    setSelectedForDelete(prev => {
      const next = new Set(prev);
      if (next.has(cardId)) next.delete(cardId);
      else next.add(cardId);
      return next;
    });
  };

  const handleDelete = async () => {
    if (selectedForDelete.size === 0) return;

    if (currentGroup && selectedForDelete.size >= currentGroup.cards.length) {
      Toast.show({ content: '不能刪除全部名片，至少保留一張', icon: 'fail' });
      return;
    }

    const confirmed = await Dialog.confirm({
      content: `確定要刪除已選的 ${selectedForDelete.size} 張名片嗎？此操作無法復原。`,
      confirmText: '確定刪除',
      cancelText: '取消',
    });

    if (!confirmed) return;

    setDeleting(true);
    try {
      for (const cardId of selectedForDelete) {
        await axios.delete(`/api/v1/cards/${cardId}`);
      }
      Toast.show({ content: `已刪除 ${selectedForDelete.size} 張名片`, icon: 'success' });
      await loadGroupByIndex(currentIndex);
    } catch (err) {
      Toast.show({ content: '刪除失敗', icon: 'fail' });
    } finally {
      setDeleting(false);
    }
  };

  const handleReview = async () => {
    if (!currentGroup) return;
    try {
      await axios.post(`/api/v1/cards/duplicates/${currentGroup.group_id}/review`);
      Toast.show({ content: '已標記全部保留', icon: 'success' });
      await loadGroupByIndex(currentIndex);
    } catch (err) {
      Toast.show({ content: '操作失敗', icon: 'fail' });
    }
  };

  const goNext = () => {
    if (currentIndex < totalGroups - 1) {
      loadGroupByIndex(currentIndex + 1);
    }
  };

  const goPrev = () => {
    if (currentIndex > 0) {
      loadGroupByIndex(currentIndex - 1);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <SpinLoading color='primary' />
      </div>
    );
  }

  if (totalGroups === 0 || !currentGroup) {
    return (
      <div className="duplicate-compare-page">
        <NavBar onBack={() => navigate('/cards')}>重複名片</NavBar>
        <div className="empty-state">
          <div className="empty-state-text">所有重複組已處理完畢</div>
          <Button
            color="primary"
            style={{ marginTop: '20px' }}
            onClick={() => navigate('/cards')}
          >
            返回名片列表
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="duplicate-compare-page">
      <NavBar onBack={() => navigate('/cards')}>
        重複名片 ({currentIndex + 1}/{totalGroups})
      </NavBar>

      <div className="duplicate-group-info">
        {currentGroup.name_zh} / {currentGroup.company_name_zh || '(無公司)'} — 共 {currentGroup.count} 張
      </div>

      <div className="duplicate-card-list">
        {currentGroup.cards.map((card) => (
          <div
            key={card.id}
            className={`duplicate-card-item ${selectedForDelete.has(card.id) ? 'selected-for-delete' : ''}`}
          >
            <div className="duplicate-card-header">
              <span className="duplicate-card-id">#{card.id}</span>
              <span className="duplicate-card-date">
                建立於 {card.created_at ? new Date(card.created_at).toLocaleDateString('zh-TW') : '未知'}
              </span>
            </div>

            <div className="duplicate-card-images">
              {card.front_cropped_image_path || card.front_image_path ? (
                <img
                  src={getImageUrl(card.front_cropped_image_path || card.front_image_path)}
                  alt="正面"
                  style={{ cursor: 'pointer' }}
                  onClick={() => ImageViewer.show({ image: getImageUrl(card.front_cropped_image_path || card.front_image_path) })}
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
              ) : (
                <div style={{ width: '48%', height: '100px', background: '#f5f5f5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>
                  無正面圖
                </div>
              )}
              {card.back_cropped_image_path || card.back_image_path ? (
                <img
                  src={getImageUrl(card.back_cropped_image_path || card.back_image_path)}
                  alt="背面"
                  style={{ cursor: 'pointer' }}
                  onClick={() => ImageViewer.show({ image: getImageUrl(card.back_cropped_image_path || card.back_image_path) })}
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
              ) : (
                <div style={{ width: '48%', height: '100px', background: '#f5f5f5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>
                  無背面圖
                </div>
              )}
            </div>

            <div className="duplicate-card-info">
              {card.position_zh && <div><span className="label">職稱:</span>{card.position_zh}</div>}
              {card.mobile_phone && <div><span className="label">手機:</span>{card.mobile_phone}</div>}
              {card.email && <div><span className="label">Email:</span>{card.email}</div>}
              {card.company_phone1 && <div><span className="label">電話:</span>{card.company_phone1}</div>}
            </div>

            <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Button
                size="mini"
                fill="outline"
                onClick={() => navigate(`/cards/${card.id}`)}
              >
                <EyeOutline /> 查看詳情
              </Button>
              <Checkbox
                checked={selectedForDelete.has(card.id)}
                onChange={() => toggleSelect(card.id)}
              >
                選擇刪除
              </Checkbox>
            </div>
          </div>
        ))}
      </div>

      <div className="duplicate-bottom-bar">
        <Button size="small" disabled={currentIndex === 0} onClick={goPrev}>
          <LeftOutline /> 上一組
        </Button>
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button size="small" color="primary" fill="outline" onClick={handleReview}>
            全部保留
          </Button>
          <Button
            size="small"
            color="danger"
            disabled={selectedForDelete.size === 0 || deleting}
            loading={deleting}
            onClick={handleDelete}
          >
            刪除已選({selectedForDelete.size})
          </Button>
        </div>
        <Button size="small" disabled={currentIndex >= totalGroups - 1} onClick={goNext}>
          下一組 <RightOutline />
        </Button>
      </div>
    </div>
  );
}
