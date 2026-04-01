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
        <h3 className="login-modal-title">登入</h3>
        {error && <div className="login-modal-error">{error}</div>}
        <div className="login-modal-input">
          <Input
            placeholder="帳號"
            value={username}
            onChange={setUsername}
            onKeyDown={handleKeyDown}
            clearable
          />
        </div>
        <div className="login-modal-input">
          <Input
            type="password"
            placeholder="密碼"
            value={password}
            onChange={setPassword}
            onKeyDown={handleKeyDown}
            clearable
          />
        </div>
        <Button
          block
          color="primary"
          size="large"
          loading={loading}
          onClick={handleLogin}
          className="login-modal-button"
        >
          登入
        </Button>
        {onClose && (
          <Button
            block
            fill="none"
            size="large"
            onClick={onClose}
            style={{ marginTop: 8, color: '#999' }}
          >
            取消
          </Button>
        )}
      </div>
    </div>
  );
};

export default LoginModal;
