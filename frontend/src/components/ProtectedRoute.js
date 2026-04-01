import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { isAuthenticated } from '../utils/auth';
import LoginModal from './LoginModal';

const ProtectedRoute = ({ children }) => {
  const navigate = useNavigate();
  const [authed, setAuthed] = useState(isAuthenticated());

  const handleLogout = useCallback(() => {
    setAuthed(false);
  }, []);

  useEffect(() => {
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [handleLogout]);

  const handleLoginSuccess = () => {
    setAuthed(true);
  };

  return (
    <>
      <LoginModal visible={!authed} onSuccess={handleLoginSuccess} onClose={() => navigate('/')} />
      {authed && children}
    </>
  );
};

export default ProtectedRoute;
