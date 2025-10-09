const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const port = 3001;

// Путь к файлу с данными
const dataFilePath = path.join(__dirname, '/src/examples.json');

// Функция для чтения данных из файла
const readData = () => {
  try {
    const data = fs.readFileSync(dataFilePath, 'utf8');
    return JSON.parse(data);
  } catch (err) {
    console.error('Ошибка чтения файла:', err);
    return [];
  }
};

// Генерация тестовых данных
const generateTestData = () => {
  const conversations = readData();
  const testData = [];
  
  const fileNames = [
    'conversation_001.mp3',
    'sales_call_2024.wav',
    'support_dialogue.aac',
    'client_meeting.m4a',
    'technical_interview.mp3',
    'business_negotiations.wav',
    'customer_feedback.aac',
    'team_briefing.m4a'
  ];
  
  const filePaths = [
    '/recordings/conversations/',
    '/audio/sales/2024/',
    '/support/calls/',
    '/meetings/client/',
    '/interviews/technical/',
    '/business/negotiations/',
    '/feedback/customers/',
    '/internal/team/'
  ];
  
  const baseDate = new Date('2024-01-01');
  
  conversations.forEach((conversation, index) => {
    const fileName = fileNames[index % fileNames.length];
    const filePath = filePaths[index % filePaths.length];
    const dateTime = new Date(baseDate.getTime() + (index * 24 * 60 * 60 * 1000)); // +1 день для каждого
    
    testData.push({
      id: index + 1,
      file_name: fileName,
      file_path: filePath,
      date_time: dateTime.toISOString()
    });
  });
  
  return testData;
};

// Разрешение CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'http://localhost:3000');
  res.header('Access-Control-Allow-Methods', 'GET');
  next();
});

// Эндпоинт для списка всех записей (только метаданные)
app.get('/api/conversations', (req, res) => {
  const testData = generateTestData();
  res.json(testData);
});

// Эндпоинт для конкретной записи по ID
app.get('/api/conversations/:id', (req, res) => {
  const conversations = readData();
  const testData = generateTestData();
  const id = parseInt(req.params.id, 10);
  
  const metaData = testData.find(item => item.id === id);
  
  if (metaData && id > 0 && id <= conversations.length) {
    const conversation = conversations[id - 1]; // Индекс в массиве начинается с 0
    
    const response = {
      id: metaData.id,
      file_data: conversation,
      file_name: metaData.file_name,
      file_path: metaData.file_path,
      date_time: metaData.date_time
    };
    
    res.json(response);
  } else {
    res.status(404).json({ error: 'Запись не найдена' });
  }
});

app.listen(port, () => {
  console.log(`Сервер запущен на http://localhost:${port}`);
});