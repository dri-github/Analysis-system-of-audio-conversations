import React, { useState } from 'react';
import { 
  Box, 
  Container, 
  Paper, 
  TextField, 
  Button, 
  Typography, 
  Tabs, 
  Tab,
  Alert,
  CircularProgress
} from '@mui/material';
import { login, register } from '../utils/auth';

const AuthPage = ({ onLoginSuccess }) => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Форма входа
  const [loginForm, setLoginForm] = useState({
    username: '',
    password: '',
  });

  // Форма регистрации
  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    setError('');
    setSuccess('');
  };

  const handleLoginChange = (e) => {
    setLoginForm({
      ...loginForm,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleRegisterChange = (e) => {
    setRegisterForm({
      ...registerForm,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (!loginForm.username || !loginForm.password) {
        throw new Error('Заполните все поля');
      }

      await login(loginForm.username, loginForm.password);
      setSuccess('Вход выполнен успешно!');
      setTimeout(() => {
        onLoginSuccess();
      }, 500);
    } catch (err) {
      setError(err.message || 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (!registerForm.username || !registerForm.email || !registerForm.password) {
        throw new Error('Заполните все обязательные поля');
      }

      if (registerForm.password !== registerForm.confirmPassword) {
        throw new Error('Пароли не совпадают');
      }

      if (registerForm.password.length < 6) {
        throw new Error('Пароль должен содержать минимум 6 символов');
      }

      await register(registerForm.username, registerForm.email, registerForm.password);
      setSuccess('Регистрация успешна! Теперь вы можете войти.');
      setTimeout(() => {
        setTabValue(0);
        setRegisterForm({
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
        });
      }, 2000);
    } catch (err) {
      setError(err.message || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: 2,
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={10}
          sx={{
            padding: 4,
            borderRadius: 3,
            background: 'rgba(255, 255, 255, 0.95)',
          }}
        >
          <Typography
            variant="h4"
            component="h1"
            align="center"
            gutterBottom
            sx={{
              fontWeight: 'bold',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 3,
            }}
          >
            Система анализа разговоров
          </Typography>

          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{ mb: 3 }}
          >
            <Tab label="Вход" />
            <Tab label="Регистрация" />
          </Tabs>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {success}
            </Alert>
          )}

          {tabValue === 0 ? (
            <form onSubmit={handleLogin}>
              <TextField
                fullWidth
                label="Имя пользователя"
                name="username"
                value={loginForm.username}
                onChange={handleLoginChange}
                margin="normal"
                required
                disabled={loading}
              />
              <TextField
                fullWidth
                label="Пароль"
                name="password"
                type="password"
                value={loginForm.password}
                onChange={handleLoginChange}
                margin="normal"
                required
                disabled={loading}
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{
                  mt: 3,
                  mb: 2,
                  py: 1.5,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5568d3 0%, #653a8f 100%)',
                  },
                }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} color="inherit" /> : 'Войти'}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              <TextField
                fullWidth
                label="Имя пользователя"
                name="username"
                value={registerForm.username}
                onChange={handleRegisterChange}
                margin="normal"
                required
                disabled={loading}
              />
              <TextField
                fullWidth
                label="Email"
                name="email"
                type="email"
                value={registerForm.email}
                onChange={handleRegisterChange}
                margin="normal"
                required
                disabled={loading}
              />
              <TextField
                fullWidth
                label="Пароль"
                name="password"
                type="password"
                value={registerForm.password}
                onChange={handleRegisterChange}
                margin="normal"
                required
                disabled={loading}
                helperText="Минимум 6 символов"
              />
              <TextField
                fullWidth
                label="Подтвердите пароль"
                name="confirmPassword"
                type="password"
                value={registerForm.confirmPassword}
                onChange={handleRegisterChange}
                margin="normal"
                required
                disabled={loading}
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{
                  mt: 3,
                  mb: 2,
                  py: 1.5,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5568d3 0%, #653a8f 100%)',
                  },
                }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} color="inherit" /> : 'Зарегистрироваться'}
              </Button>
            </form>
          )}
        </Paper>
      </Container>
    </Box>
  );
};

export default AuthPage;

