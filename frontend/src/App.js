import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { Button, Space, Card } from 'antd-mobile';
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
    <div className="App" style={{ minHeight: '100vh', background: '#f5f5f5', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
      <Card style={{ width: '90%', maxWidth: 400, margin: '0 auto', boxShadow: '0 2px 8px #eee' }}>
        <h2 style={{ marginBottom: 32 }}>名片 OCR 應用</h2>
        <Space direction="vertical" block style={{ width: '100%' }}>
          <Button color="primary" size="large" block style={{ fontSize: 18 }} onClick={() => navigate('/scan')}>
            開始掃描 / 上傳
          </Button>
          <Button color="default" size="large" block style={{ fontSize: 18 }} onClick={() => handleProtectedClick('/cards')}>
            名片管理
          </Button>
          <Button color="success" size="large" block style={{ fontSize: 18 }} onClick={() => handleProtectedClick('/spider')}>
            商機爬蟲
          </Button>
        </Space>
      </Card>
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
