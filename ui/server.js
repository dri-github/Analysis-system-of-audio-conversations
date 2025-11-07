const express = require('express');
const fs = require('fs');
const path = require('path');
const mime = require('mime-types'); // Добавь это

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

// Путь к файлу с данными
const dataFilePath2 = path.join(__dirname, '/src/sta.json');

// Функция для чтения данных из файла
const readData2 = () => {
  try {
    const data = fs.readFileSync(dataFilePath2, 'utf8');
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

// Разрешение CORS (расширил заголовки для лучшей совместимости)
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'http://localhost:3000');
  res.header('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
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

// Эндпоинт для статистики по ID
app.get('/analyze/stats/:id', (req, res) => {
  const response = readData2();
  res.json(response);
});

// Папка с аудио файлами (укажи реальный путь, где лежат твои .mp3, .wav и т.д.)
// Например, если аудио в проекте/server/audio/, то path.join(__dirname, 'audio')
const audioDir = path.join(__dirname, 'public/audio'); // ИЗМЕНИ НА СВОЙ ПУТЬ, например, path.join(__dirname, 'public/audio')

// Эндпоинт для получения аудио файла по базовому имени (без расширения или с, но в клиенте используется baseName.mp3)

app.get('/api/audio/:filename', (req, res) => {
  const filename = req.params.filename;
  const filePath = path.join(audioDir, filename);

  fs.access(filePath, fs.constants.F_OK, (err) => {
    if (err) {
      console.error(`Файл не найден: ${filePath}`);
      return res.status(404).json({ error: 'Аудио файл не найден' });
    }

    // Критично: CORS headers (разреши origin твоего фронта)
    res.setHeader('Access-Control-Allow-Origin', 'http://localhost:3000'); // Или '*' для теста
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Range');
    res.setHeader('Access-Control-Expose-Headers', 'Content-Range, Content-Length');

    // MIME type (авто-определение)
    const contentType = mime.lookup(filePath) || 'audio/mpeg';
    res.setHeader('Content-Type', contentType);

    // Range requests для seek (WaveSurfer использует)
    res.setHeader('Accept-Ranges', 'bytes');

    // Content-Length
    const stat = fs.statSync(filePath);
    res.setHeader('Content-Length', stat.size);

    // Handling range (partial content)
    const range = req.headers.range;
    if (range) {
      const parts = range.replace(/bytes=/, "").split("-");
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
      const chunksize = (end - start) + 1;
      const stream = fs.createReadStream(filePath, { start, end });

      res.writeHead(206, {
        'Content-Range': `bytes ${start}-${end}/${stat.size}`,
        'Content-Length': chunksize,
      });
      stream.pipe(res);
    } else {
      res.writeHead(200);
      fs.createReadStream(filePath).pipe(res);
    }

    // Error handling
    res.on('error', (streamErr) => {
      console.error('Ошибка стриминга:', streamErr);
      if (!res.headersSent) res.status(500).json({ error: 'Ошибка чтения файла' });
    });
  });
});

// Для pre-flight OPTIONS (CORS)
app.options('/api/audio/:filename', (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', 'http://localhost:3000');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Range');
  res.sendStatus(200);
});

app.listen(port, () => {
  console.log(`Сервер запущен на http://localhost:${port}`);
  console.log(`Аудио файлы обслуживаются из: ${audioDir} (убедись, что файлы там есть, например, conversation_001.mp3)`);
});