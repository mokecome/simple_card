import React, { useState } from 'react';
import { Input, Button } from 'antd-mobile';
import { login } from '../api/auth';
import { setToken } from '../utils/auth';
import './LoginModal.css';

const LoginModal = ({ visible, onSuccess, onClose }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!visible) return null;

  const handleLogin = async () => {
    if (!username || !password) {
      setError('請輸入帳號和密碼');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await login(username, password);
      setToken(data.access_token);
      setUsername('');
      setPassword('');
      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || '登入失敗，請確認帳號密碼');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleLogin();
  };

  return (
    <div className="login-modal-overlay">
      <div className="login-modal-card">
        <div className="login-modal-header">
          <div className="login-modal-icon">🔐</div>
          <h3 className="login-modal-title">帳號登入</h3>
          <p className="login-modal-subtitle">請輸入帳號密碼以繼續使用</p>
        </div>

        {error && <div className="login-modal-error">{error}</div>}

        <div className="login-modal-field">
          <label className="login-modal-label">帳號</label>
          <div className="login-modal-input-wrapper login-modal-input-username">
            <Input
              placeholder="請輸入帳號"
              value={username}
              onChange={setUsername}
              onKeyDown={handleKeyDown}
              clearable
            />
          </div>
        </div>

        <div className="login-modal-field">
          <label className="login-modal-label">密碼</label>
          <div className="login-modal-input-wrapper login-modal-input-password">
            <Input
              type="password"
              placeholder="請輸入密碼"
              value={password}
              onChange={setPassword}
              onKeyDown={handleKeyDown}
              clearable
            />
          </div>
        </div>

        <div className="login-modal-actions">
          <Button
            block
            color="primary"
            size="large"
            loading={loading}
            onClick={handleLogin}
            className="login-btn"
          >
            登入
          </Button>
          {onClose && (
            <button className="login-modal-close-btn" onClick={onClose}>
              返回
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginModal;
