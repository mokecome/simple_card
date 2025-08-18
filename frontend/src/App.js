import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { Button, Space, Card } from 'antd-mobile';
import 'antd-mobile/es/global';
import './App.css';
import ScanUploadPage from './pages/ScanUploadPage';
import CardManagerPage from './pages/CardManagerPage';
import AddCardPage from './pages/AddCardPage';
import CardDetailPage from './pages/CardDetailPage';

const Home = () => { 
  const navigate = useNavigate();
  return (
    <div className="App" style={{ minHeight: '100vh', background: '#f5f5f5', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
      <Card style={{ width: '90%', maxWidth: 400, margin: '0 auto', boxShadow: '0 2px 8px #eee' }}>
        <h2 style={{ marginBottom: 32 }}>名片 OCR 應用</h2>
        <Space direction="vertical" block style={{ width: '100%' }}>
          <Button color="primary" size="large" block style={{ fontSize: 18 }} onClick={() => navigate('/scan')}>
            開始掃描 / 上傳
          </Button>
          <Button color="default" size="large" block style={{ fontSize: 18 }} onClick={() => navigate('/cards')}>
            名片管理
          </Button>
        </Space>
      </Card>
    </div>
  );
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scan" element={<ScanUploadPage />} />
        <Route path="/cards" element={<CardManagerPage />} />
        <Route path="/add-card" element={<AddCardPage />} />
        <Route path="/cards/:id" element={<CardDetailPage />} />
      </Routes>
    </Router>
  );
}

export default App; 