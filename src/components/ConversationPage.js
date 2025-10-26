import React, { useState, useEffect, useRef } from 'react';
import { Box, Tabs, Tab, Typography, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { styles } from './styles';
import TabPanel from './TabPanel';
import StatsPanel from './StatsPanel';
import MessageList from './MessageList';
import { getClassLabel } from './utils';
import AudioPlayer from './AudioPlayer';

const ConversationPage = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedTab, setSelectedTab] = useState(0);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [stats, setStats] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClass, setSelectedClass] = useState('Все');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [audioSrc, setAudioSrc] = useState('');
  const [audioError, setAudioError] = useState(null);
  const [currentSeek, setCurrentSeek] = useState({ start: null, stop: null });
  const [isPlaying, setIsPlaying] = useState(false);
  const blobUrlRef = useRef(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:3001/api/conversations');
        if (!response.ok) throw new Error('Ошибка при загрузке списка разговоров');
        const conversationsData = await response.json();
        
        setConversations(conversationsData);
        
        if (conversationsData.length > 0) {
          await fetchConversationAndStats(conversationsData[0].id);
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

  const fetchConversationAndStats = async (conversationId) => {
    try {
      setLoading(true);
      setAudioError(null);
      const [conversationResponse, statsResponse] = await Promise.all([
        fetch(`http://localhost:3001/api/conversations/${conversationId}`),
        fetch(`http://localhost:3001/api/conversations/${conversationId}/stats`)
      ]);

      if (!conversationResponse.ok) throw new Error('Ошибка при загрузке разговора');
      const conversationData = await conversationResponse.json();
      setSelectedConversation(conversationData);

      const fullFileName = conversationData.file_name;
      await fetchAudio(fullFileName);

      if (!statsResponse.ok) {
        console.warn('Ошибка при загрузке статистики, используется fallback');
        setStats(null);
      } else {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch (err) {
      setError(err.message);
      setSelectedConversation({ file_data: { splitted: [] } });
      setStats(null);
      setAudioSrc('');
      setAudioError('Ошибка загрузки разговора');
    } finally {
      setLoading(false);
    }
  };

  const fetchAudio = async (fileName, signal) => {
    try {
      setAudioError(null);
      const response = await fetch(`http://localhost:3001/api/audio/${fileName}`, { signal });
      if (!response.ok) {
        throw new Error('Аудио файл не найден на сервере');
      }
      const blob = await response.blob();
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
      const url = URL.createObjectURL(blob);
      blobUrlRef.current = url;
      setAudioSrc(url);
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Fetch aborted');
        return;
      }
      console.error(err);
      setAudioSrc('');
      setAudioError(err.message || 'Не удалось загрузить аудио файл');
    }
  };

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
    setSearchTerm('');
    setSelectedClass('Все');
    if (conversations[newValue]) {
      fetchConversationAndStats(conversations[newValue].id);
    }
  };

  const fragments = selectedConversation?.file_data?.splitted || [];

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

  const uniqueClasses = Array.from(
    new Set(
      fragments && Array.isArray(fragments)
        ? fragments.map(fragment => getClassLabel(fragment).split(' (')[0] || 'N/A')
        : []
    )
  );

  const handleSeekAudio = (startStr, stopStr) => {
    console.log('handleSeekAudio: startStr =', startStr, 'stopStr =', stopStr); // Для отладки
    if (!startStr || !stopStr) {
      console.warn('handleSeekAudio: Invalid start or stop time');
      setCurrentSeek({ start: null, stop: null });
      return;
    }
    const startInSeconds = timeStrToSeconds(startStr);
    const stopInSeconds = timeStrToSeconds(stopStr);
    if (isNaN(startInSeconds) || isNaN(stopInSeconds)) {
      console.warn('handleSeekAudio: Invalid time conversion');
      setCurrentSeek({ start: null, stop: null });
      return;
    }
    setCurrentSeek({ start: startInSeconds, stop: stopInSeconds });
    setIsPlaying(true);
  };

  const timeStrToSeconds = (timeStr) => {
    if (!timeStr) return 0;
    const parts = timeStr.split(':');
    const hours = parseInt(parts[0], 10) || 0;
    const minutes = parseInt(parts[1], 10) || 0;
    const seconds = parseFloat(parts[2] || 0);
    return hours * 3600 + minutes * 60 + seconds;
  };

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, []);

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
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        zIndex: -1,
        overflowY: 'auto',
      }}
    >
      <Box sx={{ ...styles.container, height: 'auto', minHeight: '100vh', overflowY: 'auto' }}>
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

        <Box sx={{ ...styles.mainContent, overflow: 'hidden' }}>
          <Box sx={{ ...styles.leftPanel, overflowY: 'auto' }}>
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
                  label={`${conv.file_name}`}
                  id={`vertical-tab-${index}`}
                  aria-controls={`vertical-tabpanel-${index}`}
                  sx={styles.tab}
                />
              ))}
            </Tabs>
          </Box>
          <Box sx={{ ...styles.rightPanel, minHeight: 0, height: '100%' }}>
            {conversations.map((conv, index) => (
              <TabPanel 
                key={conv.id} 
                value={selectedTab} 
                index={index}
                sx={{ 
                  flex: 1, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  width: '100%',
                  height: '100%'
                }} 
              >
                <Box sx={styles.fixedSection}>
                  <StatsPanel stats={stats} />
                  
                  {selectedConversation && (
                    <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 2 }}>
                      <Typography variant="subtitle1" sx={{ mb: 1 }}>
                        Аудио файл: {selectedConversation.file_name}
                      </Typography>
                      
                      {audioError ? (
                        <Typography color="error" sx={{ mb: 1 }}>
                          {audioError}
                        </Typography>
                      ) : (
                        <AudioPlayer 
                          audioSrc={audioSrc}
                          currentSeek={currentSeek}
                          setCurrentSeek={setCurrentSeek}
                          setIsPlaying={setIsPlaying}
                          isPlaying={isPlaying}
                          fragments={fragments}
                          stats={stats}
                        />
                      )}
                    </Box>
                  )}
                  
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

                <Box sx={{ ...styles.scrollableSection, height: '100%' }}>
                  <MessageList
                    fragments={fragments}
                    searchTerm={searchTerm}
                    selectedClass={selectedClass}
                    onSeekAudio={handleSeekAudio}
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