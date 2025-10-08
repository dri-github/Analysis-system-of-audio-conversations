import React, { useState, useEffect } from 'react';
import { Box, Tabs, Tab, Typography } from '@mui/material';
import { styles } from './styles';
import TabPanel from './TabPanel';
import StatsPanel from './StatsPanel';
import MessageList from './MessageList';

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
        // Получаем список разговоров с id и fname
        const response = await fetch('http://127.0.0.1:8000/api/conversations');
        if (!response.ok) throw new Error('Ошибка при загрузке списка');
        const data = await response.json();
        setConversations(data);
        if (data.length > 0) {
          // Загружаем первый разговор сразу
          await fetchConversation(data[0].id);
          setSelectedTab(0); // Устанавливаем первую вкладку как активную
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
      const response = await fetch(`http://127.0.0.1:8000/api/conversations/${conversationId}`);
      if (!response.ok) throw new Error('Ошибка при загрузке разговора');
      setSelectedConversation(await response.json());
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
    if (conversations[newValue]) fetchConversation(conversations[newValue].id);
  };

  const fragments = selectedConversation?.splitted || [];

  if (loading) return <Typography>Загрузка...</Typography>;
  if (error) return <Typography color="error">{error}</Typography>;

  return (
    <Box sx={styles.container}>
      <Box sx={styles.analysisHeader}>
        <Typography variant="h5" color="primary" fontSize={40}>
          Анализ разговора
        </Typography>
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
                label={`Разговор ${conv.fname}`} // Отображение имени файла
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
              <StatsPanel conversation={selectedConversation} fragments={fragments} />
              <MessageList
                fragments={fragments}
                searchTerm={searchTerm}
                setSearchTerm={setSearchTerm}
                selectedClass={selectedClass}
                setSelectedClass={setSelectedClass}
              />
            </TabPanel>
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default ConversationPage;