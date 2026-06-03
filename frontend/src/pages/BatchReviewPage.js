import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Card,
  Button,
  NavBar,
  Toast,
  Tag,
  Image,
  Collapse,
  Input,
  Dialog,
  Loading,
} from 'antd-mobile';
import { CheckOutline, DeleteOutline, EditSOutline } from 'antd-mobile-icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const KEY_FIELDS = [
  { key: 'name_zh', label: '姓名' },
  { key: 'company_name_zh', label: '公司' },
  { key: 'position_zh', label: '職位' },
  { key: 'mobile_phone', label: '手機' },
  { key: 'email', label: 'Email' },
  { key: 'name_en', label: 'English Name' },
  { key: 'company_name_en', label: 'Company' },
  { key: 'position_en', label: 'Position' },
];

const BatchReviewPage = () => {
  const navigate = useNavigate();
  const { batchId } = useParams();
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [batchData, setBatchData] = useState({
    batch_id: '',
    total: 0,
    confirmed_count: 0,
    items: [],
  });
  const [actionCardId, setActionCardId] = useState(null);
  const [bulkLoading, setBulkLoading] = useState(false);

  // 載入批次名片列表
  // 注意：全域 axios interceptor 會自動帶上 Authorization header（見 src/index.js）
  const loadBatchCards = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/cards/batch/${batchId}`);
      if (res.data && res.data.success && res.data.data) {
        setBatchData({
          batch_id: res.data.data.batch_id || batchId,
          total: res.data.data.total || 0,
          confirmed_count: res.data.data.confirmed_count || 0,
          items: res.data.data.items || [],
        });
        setNotFound(false);
      } else {
        Toast.show({ content: '載入失敗', position: 'center' });
      }
    } catch (error) {
      if (error.response?.status === 404) {
        setNotFound(true);
      } else {
        console.error('載入批次名片失敗:', error);
        Toast.show({ content: '載入失敗', position: 'center' });
      }
    } finally {
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    loadBatchCards();
  }, [loadBatchCards]);

  // 本地編輯欄位（標記 _dirty）
  const handleEditField = useCallback((cardId, field, value) => {
    setBatchData((prev) => ({
      ...prev,
      items: prev.items.map((c) =>
        c.id === cardId ? { ...c, [field]: value, _dirty: true } : c
      ),
    }));
  }, []);

  // 確認單張名片（若有編輯則先 PUT）
  const handleConfirmCard = useCallback(
    async (card) => {
      setActionCardId(card.id);
      try {
        if (card._dirty) {
          const formData = new FormData();
          KEY_FIELDS.forEach(({ key }) => {
            formData.append(key, card[key] != null ? card[key] : '');
          });
          await axios.put(`${API_BASE_URL}/cards/${card.id}`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
        }
        await axios.put(`${API_BASE_URL}/cards/${card.id}/confirm`, {});
        Toast.show({ content: '已確認', position: 'center' });
        await loadBatchCards();
      } catch (error) {
        const detail =
          error.response?.data?.detail ||
          error.response?.data?.message ||
          error.message;
        Toast.show({ content: `確認失敗: ${detail}`, position: 'center' });
      } finally {
        setActionCardId(null);
      }
    },
    [loadBatchCards]
  );

  // 一次確認全部剩餘
  const handleConfirmAll = useCallback(() => {
    const remaining = batchData.items.filter((c) => !c.confirmed_at).length;
    if (remaining === 0) return;
    Dialog.confirm({
      content: `確認剩餘 ${remaining} 張名片？確認後將進入正式名片庫。`,
      confirmText: '確認',
      cancelText: '取消',
      onConfirm: async () => {
        setBulkLoading(true);
        try {
          await axios.post(
            `${API_BASE_URL}/cards/batch/${batchId}/confirm-all`,
            {}
          );
          Toast.show({ content: `已確認 ${remaining} 張`, position: 'center' });
          await loadBatchCards();
        } catch (error) {
          const detail =
            error.response?.data?.detail ||
            error.response?.data?.message ||
            error.message;
          Toast.show({ content: `操作失敗: ${detail}`, position: 'center' });
        } finally {
          setBulkLoading(false);
        }
      },
    });
  }, [batchData.items, batchId, loadBatchCards]);

  // 刪除單張
  const handleDelete = useCallback(
    (card) => {
      Dialog.confirm({
        content: `確定刪除「${card.name_zh || '(未命名)'}」？`,
        confirmText: '刪除',
        cancelText: '取消',
        onConfirm: async () => {
          try {
            await axios.delete(`${API_BASE_URL}/cards/${card.id}`);
            Toast.show({ content: '已刪除', position: 'center' });
            await loadBatchCards();
          } catch (error) {
            Toast.show({ content: '刪除失敗', position: 'center' });
          }
        },
      });
    },
    [loadBatchCards]
  );

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
        <NavBar onBack={() => navigate('/cards')}>批次審核</NavBar>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Loading />
        </div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
        <NavBar onBack={() => navigate('/cards')}>批次審核</NavBar>
        <div style={{ padding: 16, textAlign: 'center' }}>
          <div style={{ marginTop: 60, color: '#999' }}>
            此批次不存在或已被清空
          </div>
          <Button
            color="primary"
            style={{ marginTop: 16 }}
            onClick={() => navigate('/cards')}
          >
            返回名片管理
          </Button>
        </div>
      </div>
    );
  }

  const unconfirmedCount = batchData.items.filter((c) => !c.confirmed_at).length;

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#f5f5f5',
        paddingBottom: unconfirmedCount > 0 ? 80 : 16,
      }}
    >
      <NavBar onBack={() => navigate('/cards')}>批次審核</NavBar>
      <div style={{ padding: 16 }}>
        <Card style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 14 }}>
            已確認{' '}
            <strong style={{ color: '#52c41a' }}>
              {batchData.confirmed_count}
            </strong>
            {' / 共 '}
            <strong>{batchData.total}</strong>
            {' 張'}
          </div>
        </Card>

        {batchData.items.length === 0 && (
          <Card>
            <div style={{ textAlign: 'center', color: '#999', padding: 24 }}>
              此批次目前沒有名片
            </div>
          </Card>
        )}

        {batchData.items.map((card) => {
          const isConfirmed = !!card.confirmed_at;
          return (
            <Card
              key={card.id}
              style={{
                marginBottom: 8,
                opacity: isConfirmed ? 0.6 : 1,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      marginBottom: 4,
                      flexWrap: 'wrap',
                    }}
                  >
                    <strong style={{ fontSize: 15 }}>
                      {card.name_zh || '(未命名)'}
                    </strong>
                    {isConfirmed ? (
                      <Tag color="success">✓ 已確認</Tag>
                    ) : (
                      <Tag color="warning">未確認</Tag>
                    )}
                  </div>
                  <div
                    style={{
                      color: '#666',
                      fontSize: 13,
                      lineHeight: 1.5,
                      wordBreak: 'break-all',
                    }}
                  >
                    {card.company_name_zh && <div>{card.company_name_zh}</div>}
                    {card.position_zh && <div>{card.position_zh}</div>}
                    {(card.mobile_phone || card.email) && (
                      <div>
                        {card.mobile_phone} {card.email}
                      </div>
                    )}
                  </div>
                </div>
                {card.front_image_url && (
                  <Image
                    src={card.front_image_url}
                    width={60}
                    height={60}
                    fit="cover"
                    style={{ borderRadius: 4, marginLeft: 8, flexShrink: 0 }}
                  />
                )}
              </div>

              {!isConfirmed && (
                <>
                  <Collapse style={{ marginTop: 8 }}>
                    <Collapse.Panel
                      key="edit"
                      title={
                        <span>
                          <EditSOutline /> 編輯欄位
                        </span>
                      }
                    >
                      {KEY_FIELDS.map(({ key, label }) => (
                        <div key={key} style={{ marginBottom: 8 }}>
                          <div style={{ fontSize: 12, color: '#999' }}>
                            {label}
                          </div>
                          <Input
                            value={card[key] || ''}
                            onChange={(val) =>
                              handleEditField(card.id, key, val)
                            }
                          />
                        </div>
                      ))}
                    </Collapse.Panel>
                  </Collapse>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <Button
                      block
                      size="small"
                      color="primary"
                      loading={actionCardId === card.id}
                      disabled={actionCardId === card.id}
                      onClick={() => handleConfirmCard(card)}
                    >
                      <CheckOutline /> 確認
                    </Button>
                    <Button
                      size="small"
                      color="danger"
                      fill="outline"
                      disabled={actionCardId === card.id}
                      onClick={() => handleDelete(card)}
                    >
                      <DeleteOutline />
                    </Button>
                  </div>
                </>
              )}
            </Card>
          );
        })}
      </div>

      {unconfirmedCount > 0 && (
        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            padding: 12,
            background: '#fff',
            borderTop: '1px solid #eee',
            boxShadow: '0 -2px 8px rgba(0,0,0,0.04)',
            zIndex: 10,
          }}
        >
          <Button
            block
            color="primary"
            size="large"
            loading={bulkLoading}
            disabled={bulkLoading}
            onClick={handleConfirmAll}
          >
            ✓ 全部確認剩餘 {unconfirmedCount} 張
          </Button>
        </div>
      )}
    </div>
  );
};

export default BatchReviewPage;
