import React from 'react';
import { useNavigate } from 'react-router-dom';
import { NavBar } from 'antd-mobile';

const SpiderPage = () => {
  const navigate = useNavigate();
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <NavBar onBack={() => navigate('/')}>商機爬蟲</NavBar>
      <iframe
        src="/spider/?api_base=/spider"
        style={{ flex: 1, border: 'none', width: '100%' }}
        title="Ace-Spider Dashboard"
      />
    </div>
  );
};

export default SpiderPage;
