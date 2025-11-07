import React, { useState, useEffect, useRef } from 'react';
import { Box, Tabs, Tab, Typography, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { styles } from './styles';
import TabPanel from './TabPanel';
import StatsPanel from './StatsPanel';
import MessageList from './MessageList';
import { getClassLabel } from './utils';
import AudioPlayer from './AudioPlayer';

// MinIO SDK
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

// Настройки MinIO
const MINIO_CONFIG = {
  endpoint: 'http://10.200.115.155:9000',
  accessKey: 'minadmin',
  secretKey: 'minadmin',
  bucket: 'audio-processed',
  forcePathStyle: true,
};

const s3Client = new S3Client({
  region: 'us-east-1',
  endpoint: MINIO_CONFIG.endpoint,
  credentials: {
    accessKeyId: MINIO_CONFIG.accessKey,
    secretAccessKey: MINIO_CONFIG.secretKey,
  },
  forcePathStyle: MINIO_CONFIG.forcePathStyle,
});

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

  // Кэшируем signed URL для текущего файла
  const signedUrlRef = useRef('');

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://10.200.115.155/api/conversations');
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
      setAudioSrc('');
      signedUrlRef.current = ''; // Сбрасываем кэш при смене разговора

      const controller = new AbortController();
      const signal = controller.signal;

      const [conversationResponse, statsResponse] = await Promise.all([
        fetch(`http://10.200.115.155/api/conversations/${conversationId}`, { signal }),
        fetch(`http://10.200.115.155/api/analyze/stats/${conversationId}`, { signal })
      ]);

      if (!conversationResponse.ok) throw new Error('Ошибка при загрузке разговора');
      const conversationData = await conversationResponse.json();
      setSelectedConversation(conversationData);

      const fileName = conversationData.file_name;
      await fetchAudioFromMinIO(fileName);

      if (!statsResponse.ok) {
        console.warn('Статистика недоступна');
        setStats(null);
      } else {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message);
      setSelectedConversation({ file_data: { splitted: [] } });
      setStats(null);
      setAudioSrc('');
      setAudioError('Ошибка загрузки разговора');
    } finally {
      setLoading(false);
    }
  };

  const fetchAudioFromMinIO = async (fileName) => {
    try {
      setAudioError(null);
      console.log('Получаем signed URL для:', fileName);

      // Используем кэш
      if (signedUrlRef.current) {
        setAudioSrc(signedUrlRef.current);
        return;
      }

      const command = new GetObjectCommand({
        Bucket: MINIO_CONFIG.bucket,
        Key: fileName,
      });

      const signedUrl = await getSignedUrl(s3Client, command, { expiresIn: 3600 });
      signedUrlRef.current = signedUrl;
      setAudioSrc(signedUrl);

    } catch (err) {
      console.error('MinIO Error:', err);
      setAudioSrc('');
      setAudioError(err.message || 'Не удалось загрузить аудио');
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
    if (!startStr || !stopStr) {
      setCurrentSeek({ start: null, stop: null });
      return;
    }
    const startInSeconds = timeStrToSeconds(startStr);
    const stopInSeconds = timeStrToSeconds(stopStr);
    if (isNaN(startInSeconds) || isNaN(stopInSeconds)) {
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

  if (loading) return <Typography>Загрузка...</Typography>;
  if (error) return <Typography color="error">Ошибка: {error}</Typography>;

  return (
    <Box sx={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', zIndex: -1, overflowY: 'auto' }}>
      <Box sx={{ ...styles.container, height: 'auto', minHeight: '100vh', overflowY: 'auto' }}>
        <Box sx={styles.analysisHeader}>
          <Typography variant="h5" color="white" fontSize={40}>Анализ разговора</Typography>
          {selectedConversation && (
            <Typography variant="subtitle1" color="white" sx={{ mt: 1 }}>
              Файл: {selectedConversation.file_name} | Дата: {formatDate(selectedConversation.date_time)}
            </Typography>
          )}
        </Box>

        <Box sx={{ ...styles.mainContent, overflow: 'hidden' }}>
          <Box sx={{ ...styles.leftPanel, overflowY: 'auto' }}>
            <Tabs orientation="vertical" variant="scrollable" value={selectedTab} onChange={handleTabChange} sx={styles.tabs}>
              {conversations.map((conv, index) => (
                <Tab key={conv.id} label={conv.file_name} sx={styles.tab} />
              ))}
            </Tabs>
          </Box>

          <Box sx={{ ...styles.rightPanel, minHeight: 0, height: '100%' }}>
            {conversations.map((conv, index) => (
              <TabPanel key={conv.id} value={selectedTab} index={index} sx={{ flex: 1, display: 'flex', flexDirection: 'column', width: '100%', height: '100%' }}>
                <Box sx={styles.fixedSection}>
                  <StatsPanel stats={stats} />
                  
                  {selectedConversation && (
                    <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 2 }}>
                      <Typography variant="subtitle1" sx={{ mb: 1 }}>Аудио: {selectedConversation.file_name}</Typography>
                      
                      {audioError ? (
                        <Typography color="error">{audioError}</Typography>
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
                    <TextField fullWidth placeholder="Поиск..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} size="small" sx={{ flex: 1 }} />
                    <FormControl size="small" sx={{ minWidth: 150, ml: 2 }}>
                      <InputLabel>Класс</InputLabel>
                      <Select value={selectedClass} onChange={(e) => setSelectedClass(e.target.value)} label="Класс">
                        <MenuItem value="Все">Все</MenuItem>
                        {uniqueClasses.map((cls) => <MenuItem key={cls} value={cls}>{cls}</MenuItem>)}
                      </Select>
                    </FormControl>
                  </Box>
                </Box>

                <Box sx={{ ...styles.scrollableSection, height: '100%' }}>
                  <MessageList fragments={fragments} searchTerm={searchTerm} selectedClass={selectedClass} onSeekAudio={handleSeekAudio} />
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