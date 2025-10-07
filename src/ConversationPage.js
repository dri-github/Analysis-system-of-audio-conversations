import React, { useState } from 'react';
import { 
  Box, 
  Tabs, 
  Tab, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  Divider,
  TextField, // Для поиска
  FormControl, // Для dropdown
  InputLabel,
  Select,
  MenuItem, // Для опций dropdown
} from '@mui/material';
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
  const [searchTerm, setSearchTerm] = useState(''); // Для поиска по словам
  const [selectedClass, setSelectedClass] = useState('Все'); // Для фильтра по классу

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
    // Сброс фильтров при смене вкладки
    setSearchTerm('');
    setSelectedClass('Все');
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
      baseColor = baseColor === "#e8f5e8" ? '#e1f5fe' : baseColor; // Для спикера 0 — голубой акцент
    } else {
      baseColor = baseColor === "#e1f5fe" ? '#f0f0f0' : baseColor; // Для остальных — серый акцент
    }

    return baseColor;
  };

  // Извлечение уникальных классов для dropdown
  const uniqueClasses = Array.from(new Set(fragments.map(fragment => getClassLabel(fragment).split(' (')[0] || 'N/A')));

  // Фильтрация фрагментов
  const filteredFragments = fragments.filter(fragment => {
    const matchesSearch = fragment.text.toLowerCase().includes(searchTerm.toLowerCase());
    const fragmentClass = getClassLabel(fragment).split(' (')[0] || 'N/A';
    const matchesClass = selectedClass === 'Все' || fragmentClass === selectedClass;
    return matchesSearch && matchesClass;
  });

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* Левая панель: Вкладки для разговоров */}
      <Box sx={{ width: '20%', borderRight: 1, borderColor: 'divider', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
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
        width: '80%', 
        py: 3, // Вертикальный padding сохранён
        px: 2, // Горизонтальный padding уменьшен
        overflowY: 'auto',
        boxShadow: 'inset -2px 0 8px rgba(0,0,0,0.05)',
        boxSizing: 'border-box', // Padding не выходит за ширину
      }}>
        {conversations.map((conv, index) => (
          <TabPanel key={index} value={selectedTab} index={index}>
            <Typography variant="h5" gutterBottom sx={{ boxShadow: '0 1px 3px rgba(0,0,0,0.1)', p: 1, borderRadius: 1, display: 'inline-block' }}>
              Разговор от {conv.created}
            </Typography>
            <Typography variant="subtitle1" gutterBottom>
              Спикеры: {conv.speakers.length} | Фрагментов: {fragments.length} | Найдено: {filteredFragments.length}
            </Typography>
            <Divider sx={{ mb: 2 }} />

            {/* Контролы фильтрации: Поиск + Dropdown */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Поиск по словам..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                size="small"
                sx={{ flex: 1 }}
              />
              <FormControl variant="outlined" size="small" sx={{ minWidth: 150 }}>
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

            {filteredFragments.length > 0 ? (
              <List sx={{ bgcolor: 'background.paper', width: '100%' }}>
                {filteredFragments.map((fragment, fragIndex) => {
                  const style = getSpeakerStyle(fragment.speaker);
                  const bgColor = getClassColor(fragment); // Цвет по классу + спикеру
                  return (
                    <ListItem
                      key={fragIndex}
                      alignItems="flex-start"
                      sx={{
                        ...style,
                        mb: 2, // Увеличил отступ для теней
                        width: '100%', // Полная ширина для правильной прижимки
                        justifyContent: 'stretch', // Растягивает содержимое по ширине
                      }}
                    >
                      <Box
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          width: 'auto', // Динамическая ширина
                          flex: 1, // Растягивается в родителе
                          maxWidth: '80%', // Лимит, чтобы не растягивалось слишком
                          wordBreak: 'break-word', // Для длинных текстов
                          backgroundColor: bgColor, // Динамический цвет по классу + спикеру
                          borderLeft: `3px solid ${bgColor === "#fafafa" ? "#ccc" : bgColor}`, // Легкая рамка слева для акцента
                          boxShadow: 1, // Тень для пузыря сообщения
                          transition: 'box-shadow 0.2s ease', // Плавный hover-эффект
                          '&:hover': {
                            boxShadow: 3, // Усиленная тень при наведении
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
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                Фрагменты не найдены по текущим фильтрам.
              </Typography>
            )}
          </TabPanel>
        ))}
      </Box>
    </Box>
  );
};

export default ConversationPage;