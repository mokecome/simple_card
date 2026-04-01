import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import 'antd-mobile/es/global';
import './App.css';
import ScanUploadPage from './pages/ScanUploadPage';
import CardManagerPage from './pages/CardManagerPage';
import AddCardPage from './pages/AddCardPage';
import CardDetailPage from './pages/CardDetailPage';
import SpiderPage from './pages/SpiderPage';
import ProtectedRoute from './components/ProtectedRoute';
import LoginModal from './components/LoginModal';
import { isAuthenticated } from './utils/auth';
import './components/Home.css';

const Home = () => {
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(false);
  const [pendingPath, setPendingPath] = useState(null);

  const handleProtectedClick = (path) => {
    if (isAuthenticated()) {
      navigate(path);
    } else {
      setPendingPath(path);
      setShowLogin(true);
    }
  };

  const handleLoginSuccess = () => {
    setShowLogin(false);
    if (pendingPath) {
      navigate(pendingPath);
      setPendingPath(null);
    }
  };

  return (
    <div className="home-page">
      <div className="home-brand">
        <div className="home-logo">📇</div>
        <h1 className="home-title">名片 OCR 應用</h1>
        <p className="home-subtitle">智慧名片辨識與管理平台</p>
      </div>

      <div className="home-features">
        <div className="feature-card feature-card--scan" onClick={() => navigate('/scan')}>
          <div className="feature-icon">📷</div>
          <div className="feature-text">
            <div className="feature-name">開始掃描 / 上傳</div>
            <div className="feature-desc">拍照或上傳名片，自動辨識文字</div>
          </div>
          <span className="feature-arrow">›</span>
        </div>

        <div className="feature-card feature-card--cards" onClick={() => handleProtectedClick('/cards')}>
          <div className="feature-icon">📋</div>
          <div className="feature-text">
            <div className="feature-name">名片管理</div>
            <div className="feature-desc">搜尋、篩選、匯出所有名片資料</div>
          </div>
          <span className="feature-lock">需登入</span>
          <span className="feature-arrow">›</span>
        </div>

        <div className="feature-card feature-card--spider" onClick={() => handleProtectedClick('/spider')}>
          <div className="feature-icon">🕸️</div>
          <div className="feature-text">
            <div className="feature-name">商機爬蟲</div>
            <div className="feature-desc">自動抓取潛在商業機會資訊</div>
          </div>
          <span className="feature-lock">需登入</span>
          <span className="feature-arrow">›</span>
        </div>
      </div>

      <div className="home-footer">
        <p className="home-footer-text">Star-Bit Innovation Co., Ltd.</p>
      </div>

      <LoginModal visible={showLogin} onSuccess={handleLoginSuccess} onClose={() => setShowLogin(false)} />
    </div>
  );
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scan" element={<ScanUploadPage />} />
        <Route path="/cards" element={<ProtectedRoute><CardManagerPage /></ProtectedRoute>} />
        <Route path="/add-card" element={<ProtectedRoute><AddCardPage /></ProtectedRoute>} />
        <Route path="/cards/:id" element={<ProtectedRoute><CardDetailPage /></ProtectedRoute>} />
        <Route path="/spider" element={<ProtectedRoute><SpiderPage /></ProtectedRoute>} />
      </Routes>
    </Router>
  );
}

export default App;
