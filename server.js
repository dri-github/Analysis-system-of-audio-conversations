const express = require('express');
const fs = require('fs').promises;
const path = require('path');

const app = express();
const port = 3001;

const filePath = path.join(__dirname, '/src/examples.json');

let conversations = [];

const loadData = async () => {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    conversations = JSON.parse(data);
    conversations.forEach((conv, index) => {
      if (!conv.id) conv.id = index + 1;
    });
  } catch (error) {
    console.error('Ошибка при чтении файла:', error);
    conversations = [];
  }
};

loadData();

// Разрешение CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'http://localhost:3000'); // Разрешить только порт 3000
  res.header('Access-Control-Allow-Methods', 'GET');
  next();
});

app.get('/api/conversations', (req, res) => {
  const ids = conversations.map(conv => conv.id);
  res.json(ids);
});

app.get('/api/conversations/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  const conversation = conversations.find(conv => conv.id === id);
  if (conversation) {
    res.json(conversation);
  } else {
    res.status(404).json({ error: 'Разговор не найден' });
  }
});

app.listen(port, () => {
  console.log(`Сервер запущен на http://localhost:${port}`);
});