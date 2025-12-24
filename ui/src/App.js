import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ConversationPage from './components/ConversationPage';
import AuthPage from './components/AuthPage';
import { isAuthenticated, logout } from './utils/auth';
import { Box, Button, AppBar, Toolbar, Typography } from '@mui/material';

import './App.css'; // Если нужны дополнительные стили

function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());

  useEffect(() => {
    setAuthenticated(isAuthenticated());
  }, []);

  const handleLoginSuccess = () => {
    setAuthenticated(true);
  };

  const handleLogout = () => {
    logout();
    setAuthenticated(false);
  };

  return (
    <Router>
      <div className="App">
        {authenticated && (
          <AppBar position="static" sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <Toolbar>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                Система анализа разговоров
              </Typography>
              <Button color="inherit" onClick={handleLogout}>
                Выйти
              </Button>
            </Toolbar>
          </AppBar>
        )}
        <Routes>
          <Route
            path="/login"
            element={
              authenticated ? (
                <Navigate to="/" replace />
              ) : (
                <AuthPage onLoginSuccess={handleLoginSuccess} />
              )
            }
          />
          <Route
            path="/"
            element={
              authenticated ? (
                <ConversationPage />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;