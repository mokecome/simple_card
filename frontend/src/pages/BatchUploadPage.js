import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Space,
  Card,
  Toast,
  NavBar,
  Loading,
  Image,
  Dialog,
  ProgressBar
} from 'antd-mobile';
import { AddOutline, CloseOutline } from 'antd-mobile-icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const MAX_FILES = 50;

const STAGE = {
  SELECT: 'select',       // 選圖 + 預覽
  UPLOADING: 'uploading', // 上傳中
  DONE: 'done'            // 上傳完成，可離開
};

const ALLOWED_TYPES = ['image/jpeg', 'image/png'];

const BatchUploadPage = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [stage, setStage] = useState(STAGE.SELECT);
  const [images, setImages] = useState([]); // [{file, preview, id}]
  const [uploadProgress, setUploadProgress] = useState(0);

  // 進入頁面時，檢查是否有未完成的任務
  useEffect(() => {
    const stored = localStorage.getItem('batch_upload_task');
    if (!stored) return;

    let parsed;
    try {
      parsed = JSON.parse(stored);
    } catch (e) {
      localStorage.removeItem('batch_upload_task');
      return;
    }

    const { taskId } = parsed || {};
    if (!taskId) {
      localStorage.removeItem('batch_upload_task');
      return;
    }

    axios.get(`${API_BASE_URL}/ocr/batch-status/${taskId}`)
      .then(res => {
        const status = res.data?.data?.status;
        if (status === 'processing' || status === 'pending') {
          Dialog.confirm({
            content: '你有一個批次任務正在背景處理中，前往名片管理頁查看？',
            onConfirm: () => navigate('/cards?confirmed=false')
          });
        } else {
          // completed / failed → 清掉
          localStorage.removeItem('batch_upload_task');
        }
      })
      .catch(() => {
        // 404 或其它錯誤都靜默清掉
        localStorage.removeItem('batch_upload_task');
      });
  }, [navigate]);

  // 元件卸載時釋放縮圖記憶體
  // 注意：deps 留空（[]），cleanup 透過 functional setState 取最新 images 快照，
  // 避免把 images 放進 deps 造成每次 render 都重綁 cleanup 而提早釋放
  useEffect(() => {
    return () => {
      setImages(current => {
        current.forEach(img => URL.revokeObjectURL(img.preview));
        return current;
      });
    };
  }, []);

  // 選圖 + 50 張上限驗證 + 格式驗證
  const handleSelectFiles = useCallback((e) => {
    const newFiles = Array.from(e.target.files || []);
    e.target.value = '';

    if (!newFiles.length) return;

    // 檔案格式驗證（只接受 JPG / PNG）
    const invalidFiles = newFiles.filter(f => !ALLOWED_TYPES.includes(f.type));
    if (invalidFiles.length) {
      Toast.show({
        content: `${invalidFiles.length} 張不是支援的格式（僅支援 JPG、PNG）`,
        position: 'center'
      });
      return;
    }

    // 50 張上限檢查（整批拒收，要求重新選）
    if (images.length + newFiles.length > MAX_FILES) {
      Toast.show({
        content: `最多支援 ${MAX_FILES} 張，目前已選 ${images.length} 張，這次想新增 ${newFiles.length} 張，請重新選擇`,
        position: 'center',
        duration: 3000
      });
      return;
    }

    const offset = images.length;
    const newImages = newFiles.map((file, i) => ({
      file,
      preview: URL.createObjectURL(file),
      id: `img_${Date.now()}_${offset + i}`
    }));

    setImages(prev => [...prev, ...newImages]);
  }, [images]);

  // 刪除單張圖（釋放 objectURL）
  const handleRemoveImage = useCallback((imageId) => {
    setImages(prev => {
      const target = prev.find(img => img.id === imageId);
      if (target) URL.revokeObjectURL(target.preview);
      return prev.filter(img => img.id !== imageId);
    });
  }, []);

  // 上傳（fire-and-forget）
  const handleStartUpload = useCallback(async () => {
    if (!images.length) {
      Toast.show({ content: '請先選取圖片', position: 'center' });
      return;
    }

    setStage(STAGE.UPLOADING);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      images.forEach(img => formData.append('files', img.file));

      // V1：每張圖一組正面，back_index 一律 null（預留 V2 雙面配對）
      const groupPayload = images.map((_, i) => ({
        front_index: i,
        back_index: null
      }));
      formData.append('groups', JSON.stringify(groupPayload));

      const res = await axios.post(`${API_BASE_URL}/ocr/batch-upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 分鐘
        onUploadProgress: (e) => {
          if (e.total) {
            setUploadProgress(Math.round((e.loaded * 100) / e.total));
          }
        }
      });

      if (res.data?.success) {
        localStorage.setItem('batch_upload_task', JSON.stringify({
          taskId: res.data.task_id,
          batchId: res.data.batch_id,
          totalGroups: res.data.total_groups,
          startedAt: new Date().toISOString()
        }));
        setStage(STAGE.DONE);
      } else {
        throw new Error(res.data?.message || '上傳失敗');
      }
    } catch (error) {
      Toast.show({
        content: `上傳失敗: ${error.response?.data?.detail || error.message}`,
        position: 'center'
      });
      setStage(STAGE.SELECT);
    }
  }, [images]);

  // 「再上傳一批」重設
  const handleReset = useCallback(() => {
    images.forEach(img => URL.revokeObjectURL(img.preview));
    setImages([]);
    setUploadProgress(0);
    setStage(STAGE.SELECT);
    localStorage.removeItem('batch_upload_task');
  }, [images]);

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <NavBar onBack={() => navigate(-1)}>批次上傳辨識</NavBar>

      {/* ===== 階段一：選圖 + 預覽 ===== */}
      {stage === STAGE.SELECT && (
        <div style={{ padding: 16 }}>
          <Card style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 14, color: '#666', lineHeight: 1.6 }}>
              📦 每張圖會被視為一張名片正面，最多可選 {MAX_FILES} 張<br />
              💡 雙面名片功能將在下一期推出
            </div>
          </Card>

          <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
            已選取 <strong>{images.length}</strong> / {MAX_FILES} 張
          </div>

          <Button
            block
            color="primary"
            size="large"
            onClick={() => fileInputRef.current?.click()}
            disabled={images.length >= MAX_FILES}
            style={{ marginBottom: 16 }}
          >
            <AddOutline /> 選取名片圖片
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            multiple
            onChange={handleSelectFiles}
            style={{ display: 'none' }}
          />

          {/* 縮圖網格（3 欄 grid） */}
          {images.length > 0 && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 8,
              marginBottom: 16
            }}>
              {images.map((img, i) => (
                <div
                  key={img.id}
                  style={{
                    position: 'relative',
                    aspectRatio: '1',
                    borderRadius: 8,
                    overflow: 'hidden',
                    background: '#fff'
                  }}
                >
                  <Image src={img.preview} width="100%" height="100%" fit="cover" />
                  <div style={{
                    position: 'absolute', top: 4, left: 4,
                    background: 'rgba(0,0,0,0.5)', color: '#fff',
                    borderRadius: 4, padding: '2px 6px', fontSize: 11
                  }}>
                    #{i + 1}
                  </div>
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label={`移除第 ${i + 1} 張圖片`}
                    onClick={() => handleRemoveImage(img.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleRemoveImage(img.id);
                      }
                    }}
                    style={{
                      position: 'absolute', top: 4, right: 4,
                      background: 'rgba(255,77,79,0.9)', color: '#fff',
                      width: 24, height: 24, borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      cursor: 'pointer'
                    }}
                  >
                    <CloseOutline fontSize={14} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {images.length > 0 && (
            <Button
              block
              color="success"
              size="large"
              onClick={handleStartUpload}
            >
              開始辨識（共 {images.length} 張名片）
            </Button>
          )}
        </div>
      )}

      {/* ===== 階段二：上傳中 ===== */}
      {stage === STAGE.UPLOADING && (
        <div style={{ padding: 16, textAlign: 'center' }}>
          <Loading color="primary" />
          <div style={{ margin: '16px 0', fontSize: 16 }}>正在上傳圖片...</div>
          <ProgressBar percent={uploadProgress} />
          <div style={{ marginTop: 8, color: '#999' }}>{uploadProgress}%</div>
          <div style={{ marginTop: 16, color: '#ff9500', fontSize: 13 }}>
            ⚠️ 上傳中請勿離開頁面
          </div>
        </div>
      )}

      {/* ===== 階段三：上傳完成（可離開） ===== */}
      {stage === STAGE.DONE && (
        <div style={{ padding: 16 }}>
          <Card>
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <div style={{ fontSize: 48, color: '#52c41a' }}>✓</div>
              <div style={{ fontSize: 18, fontWeight: 'bold', marginTop: 8 }}>
                已收到 {images.length} 張名片！
              </div>
              <div style={{ color: '#666', marginTop: 16, lineHeight: 1.6 }}>
                OCR 將在背景處理（約 {Math.ceil(images.length * 0.3)} - {Math.ceil(images.length * 0.6)} 分鐘）<br />
                可離開頁面、關掉瀏覽器或鎖螢幕走人<br />
                完成後可在「名片管理」→「待確認」查看結果
              </div>
            </div>
          </Card>
          <Space direction="vertical" block style={{ marginTop: 16 }}>
            <Button
              block
              color="primary"
              size="large"
              onClick={() => navigate('/cards?confirmed=false')}
            >
              前往名片管理查看
            </Button>
            <Button
              block
              size="large"
              onClick={handleReset}
            >
              再上傳一批
            </Button>
          </Space>
        </div>
      )}
    </div>
  );
};

export default BatchUploadPage;
