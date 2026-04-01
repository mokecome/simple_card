import React, { useState, useEffect, useCallback } from 'react';
import { isAuthenticated } from '../utils/auth';
import LoginModal from './LoginModal';

const ProtectedRoute = ({ children }) => {
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
      <LoginModal visible={!authed} onSuccess={handleLoginSuccess} />
      {authed && children}
    </>
  );
};

export default ProtectedRoute;
