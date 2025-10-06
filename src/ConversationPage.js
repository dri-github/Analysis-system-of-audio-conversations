import React, { useState } from 'react';
import { Box, Tabs, Tab, Typography, List, ListItem, ListItemText, Divider } from '@mui/material';
import data from './examples.json'; // Импорт JSON (массив для нескольких разговоров)

// Обернем данные в массив для симуляции (теперь data — массив)
const conversations = data; // Если один — [data]

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`vertical-tabpanel-${index}`}
      aria-labelledby={`vertical-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const ConversationPage = () => {
  const [selectedTab, setSelectedTab] = useState(0);

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  const selectedConversation = conversations[selectedTab];
  const fragments = selectedConversation?.splitted || [];

  // Функция для извлечения класса (первый из classes)
  const getClassLabel = (fragment) => {
    const classifiers = fragment.classifiers?.smc?.["Оценка_разговора_1"]?.classes;
    if (classifiers && classifiers.length > 0) {
      const firstClass = classifiers[0];
      return `${firstClass.class} (confidence: ${firstClass.confidence.toFixed(2)})`;
    }
    return "N/A";
  };

  // Функция для извлечения эмоции
  const getEmotionLabel = (fragment) => {
    const emotion = fragment.voice_analysis?.emotion;
    if (emotion && emotion.class) {
      return `${emotion.class} (confidence: ${emotion.confidence.toFixed(2)})`;
    }
    return "N/A";
  };

  // Функция для определения стороны и стиля по спикеру (обновлено: спикер 0 — справа, остальные — слева)
  const getSpeakerStyle = (speakerId) => {
    const isSpeakerZero = speakerId === 0; // Спикер 0 — справа, остальные — слева
    return {
      justifyContent: isSpeakerZero ? 'flex-end' : 'flex-start',
      flexDirection: isSpeakerZero ? 'row-reverse' : 'row',
      ml: isSpeakerZero ? 'auto' : 0, // Отступы для прижимки
      mr: isSpeakerZero ? 0 : 'auto',
    };
  };

  // Функция для цвета по классу (с базовым оттенком по спикеру для комбинации)
  const getClassColor = (fragment) => {
    const className = fragment.classifiers?.smc?.["Оценка_разговора_1"]?.classes?.[0]?.class || "N/A";
    const colorMap = {
      "Приветствие": "#e8f5e8", // Светло-зеленый
      "Общие вопросы": "#e3f2fd", // Светло-синий
      "Запрос информации": "#fff3e0", // Светло-оранжевый
      "Жалоба": "#ffebee", // Светло-красный
      "Возражения клиента": "#f3e5f5", // Светло-фиолетовый
      "завершение_сессии": "#f5f5f5", // Светло-серый
      "Оператор": "#e1f5fe", // Светло-голубой
      "N/A": "#fafafa", // Нейтральный
    };
    let baseColor = colorMap[className] || "#fafafa";

    // Комбинируем с базовым по спикеру (спикер 0 — голубоватый оттенок, остальные — серый)
    const speakerId = fragment.speaker;
    if (speakerId === 0) {
      baseColor = baseColor.replace(/e8f5e8/g, '#e1f5fe'); // Для спикера 0 — голубой акцент
    } else {
      baseColor = baseColor.replace(/e1f5fe/g, '#f0f0f0'); // Для остальных — серый акцент
    }

    return baseColor;
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* Левая панель: Вкладки для разговоров */}
      <Box sx={{ width: '30%', borderRight: 1, borderColor: 'divider', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <Tabs
          orientation="vertical"
          variant="scrollable"
          value={selectedTab}
          onChange={handleTabChange}
          aria-label="Conversations tabs"
          sx={{ borderRight: 1, borderColor: 'divider' }}
        >
          {conversations.map((conv, index) => (
            <Tab
              key={index}
              label={`Разговор ${index + 1} (${conv.created})`}
              id={`vertical-tab-${index}`}
              aria-controls={`vertical-tabpanel-${index}`}
              sx={{
                // Тень для активной вкладки
                ...(selectedTab === index && {
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                  backgroundColor: 'rgba(0,0,0,0.04)',
                }),
              }}
            />
          ))}
        </Tabs>
      </Box>

      {/* Правая панель: Диалог выбранного разговора */}
      <Box sx={{ 
        width: '70%', 
        p: 3, 
        overflowY: 'auto',
        boxShadow: 'inset -2px 0 8px rgba(0,0,0,0.05)', // Тень для разделения панелей
      }}>
        {conversations.map((conv, index) => (
          <TabPanel key={index} value={selectedTab} index={index}>
            <Typography variant="h5" gutterBottom sx={{ boxShadow: '0 1px 3px rgba(0,0,0,0.1)', p: 1, borderRadius: 1, display: 'inline-block' }}>
              Разговор от {conv.created}
            </Typography>
            <Typography variant="subtitle1" gutterBottom>
              Спикеры: {conv.speakers.length} | Фрагментов: {fragments.length}
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <List sx={{ bgcolor: 'background.paper' }}>
              {fragments.map((fragment, fragIndex) => {
                const style = getSpeakerStyle(fragment.speaker);
                const bgColor = getClassColor(fragment); // Цвет по классу + спикеру
                return (
                  <ListItem
                    key={fragIndex}
                    alignItems="flex-start"
                    sx={{
                      ...style,
                      mb: 2, // Увеличил отступ для теней
                      width: '70%', // Полная ширина для правильной прижимки
                    }}
                  >
                    <Box
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        maxWidth: '70%',
                        wordBreak: 'break-word', // Для длинных текстов
                        backgroundColor: bgColor, // Динамический цвет по классу + спикеру
                        borderLeft: `3px solid ${bgColor === "#fafafa" ? "#ccc" : bgColor}`, // Легкая рамка слева для акцента
                        boxShadow: 1, // Тень для пузыря сообщения (MUI shadow 1: 0px 1px 3px rgba(0,0,0,0.2))
                        transition: 'box-shadow 0.2s ease', // Плавный hover-эффект
                        '&:hover': {
                          boxShadow: 3, // Усиленная тень при наведении (MUI shadow 3)
                        },
                      }}
                    >
                      <Typography variant="body1" fontWeight="bold" gutterBottom>
                        Спикер {fragment.speaker}: {fragment.text}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8em' }}>
                        <strong>Время:</strong> {fragment.start} - {fragment.stop} ({fragment.duration})<br />
                        <strong>Эмоция:</strong> {getEmotionLabel(fragment)}<br />
                        <strong>Класс:</strong> {getClassLabel(fragment)}
                      </Typography>
                    </Box>
                  </ListItem>
                );
              })}
            </List>
          </TabPanel>
        ))}
      </Box>
    </Box>
  );
};

export default ConversationPage;