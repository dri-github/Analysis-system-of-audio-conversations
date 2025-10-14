import React, { useState, useEffect } from 'react';
import { Box, Tabs, Tab, Typography, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { styles } from './styles';
import TabPanel from './TabPanel';
import StatsPanel from './StatsPanel';
import MessageList from './MessageList';
import { getClassLabel } from './utils';

const ConversationPage = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedTab, setSelectedTab] = useState(0);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClass, setSelectedClass] = useState('Все');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://api:8000/api/conversations');
        if (!response.ok) throw new Error('Ошибка при загрузке списка разговоров');
        const conversationsData = await response.json();
        
        // Теперь сервер возвращает массив объектов с полями id, file_name, file_path, date_time
        setConversations(conversationsData);
        
        if (conversationsData.length > 0) {
          await fetchConversation(conversationsData[0].id);
          setSelectedTab(0);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, []);

  const fetchConversation = async (conversationId) => {
    try {
      setLoading(true);
      const response = await fetch(`http://api:8000/api/conversations/${conversationId}`);
      if (!response.ok) throw new Error('Ошибка при загрузке разговора');
      const data = await response.json();
      
      // Теперь сервер возвращает объект с полями:
      // id, file_data, file_name, file_path, date_time
      setSelectedConversation(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
    setSearchTerm('');
    setSelectedClass('Все');
    if (conversations[newValue]) {
      fetchConversation(conversations[newValue].id);
    }
  };

  // Получаем fragments из file_data (основные данные разговора)
  const fragments = selectedConversation?.file_data?.splitted || [];

  // Форматирование даты для отображения
  const formatDate = (dateString) => {
    if (!dateString) return 'Нет даты';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Нет даты';
    }
  };

  // Извлечение уникальных классов для dropdown
  const uniqueClasses = Array.from(
    new Set(
      fragments && Array.isArray(fragments) 
        ? fragments.map(fragment => getClassLabel(fragment).split(' (')[0] || 'N/A')
        : []
    )
  );

  if (loading) return <Typography>Загрузка...</Typography>;
  if (error) return <Typography color="error">Ошибка: {error}</Typography>;

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        zIndex: -1,
      }}
    >
      <Box sx={styles.container}>
        <Box sx={styles.analysisHeader}>
          <Typography variant="h5" color="white" fontSize={40}>
            Анализ разговора
          </Typography>
          {selectedConversation && (
            <Typography variant="subtitle1" color="white" sx={{ mt: 1 }}>
              Файл: {selectedConversation.file_name} | 
              Дата: {formatDate(selectedConversation.date_time)}
            </Typography>
          )}
        </Box>

        <Box sx={styles.mainContent}>
          <Box sx={styles.leftPanel}>
            <Tabs
              orientation="vertical"
              variant="scrollable"
              value={selectedTab}
              onChange={handleTabChange}
              aria-label="Conversations tabs"
              sx={styles.tabs}
            >
              {conversations.map((conv, index) => (
                <Tab
                  key={conv.id}
                  label={`Разговор ${conv.id} (${formatDate(conv.date_time)})`}
                  id={`vertical-tab-${index}`}
                  aria-controls={`vertical-tabpanel-${index}`}
                  sx={styles.tab}
                />
              ))}
            </Tabs>
          </Box>
          <Box sx={styles.rightPanel}>
            {conversations.map((conv, index) => (
              <TabPanel key={conv.id} value={selectedTab} index={index}>
                {/* Фиксированная секция со статистикой и фильтрами */}
                <Box sx={styles.fixedSection}>
                  {/* Передаем file_data в StatsPanel как основной объект разговора */}
                  <StatsPanel 
                    conversation={selectedConversation?.file_data} 
                    fragments={fragments} 
                  />
                  
                  {/* Фильтры из MessageList */}
                  <Box sx={styles.filterControls}>
                    <TextField
                      fullWidth
                      variant="outlined"
                      placeholder="Поиск по словам..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      size="small"
                      sx={{ flex: 1 }}
                    />
                    <FormControl variant="outlined" size="small" sx={{ minWidth: 150, ml: 2 }}>
                      <InputLabel>Класс</InputLabel>
                      <Select
                        value={selectedClass}
                        onChange={(e) => setSelectedClass(e.target.value)}
                        label="Класс"
                      >
                        <MenuItem value="Все">Все</MenuItem>
                        {uniqueClasses.map((cls) => (
                          <MenuItem key={cls} value={cls}>{cls}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Box>
                </Box>

                {/* Прокручиваемая секция с сообщениями */}
                <Box sx={styles.scrollableSection}>
                  <MessageList
                    fragments={fragments}
                    searchTerm={searchTerm}
                    selectedClass={selectedClass}
                  />
                </Box>
              </TabPanel>
            ))}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default ConversationPage;
