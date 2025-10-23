import React from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';
import { LinearProgress } from '@mui/material';
import { styles } from './styles';
import conversationStats from '../sta.json'; // Импорт JSON файла для fallback

const StatsPanel = ({ stats }) => {
  // Используем данные из props, если они есть, иначе fallback на JSON
  const safeStats = stats ;

  // Функция для форматирования времени из миллисекунд в формат MM:SS
  const formatTime = (ms) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <Box sx={styles.statsPanel}>
      <Typography variant="h6" gutterBottom sx={{ fontSize: '2rem' }}>
        Статистика разговора
      </Typography>

      {/* Общая статистика */}
      <Box sx={styles.statsGrid}>
        <Typography><strong>Общее время:</strong> {safeStats.totalDuration}</Typography>
        <Typography><strong>Спикеров:</strong> {safeStats.speakerCount}</Typography>
        <Typography><strong>Средняя длина фрагмента:</strong> {safeStats.avgFragmentDuration} сек</Typography>
        <Typography><strong>Топ эмоция:</strong> {safeStats.topEmotion}</Typography>
        <Typography><strong>Топ класс:</strong> {safeStats.topClass}</Typography>
        <Typography><strong>Процент наложений:</strong> {safeStats.overlapDetails.percentage}%</Typography>
      </Box>

      {/* Бар чарт для спикеров */}
      <Box sx={styles.chartContainer}>
        <Typography variant="subtitle1" sx={styles.chartTitle}>
          Процент времени спикеров
        </Typography>
        <BarChart
          series={[{ data: safeStats.speakerStats.map(s => s.percentage) }]}
          xAxis={[{ scaleType: 'band', data: safeStats.speakerStats.map(s => `Спикер ${s.id} (${s.gender}, ${s.age})`) }]}
          height={300}
          sx={styles.barChart}
        />
      </Box>

      {/* Бар чарт для классов */}
      <Box sx={styles.chartContainer}>
        <Typography variant="subtitle1" sx={styles.chartTitle}>
          Статистика классов (кол-во и %)
        </Typography>
        <BarChart
          series={[{ data: safeStats.classStats.map(c => c.percentage) }]}
          xAxis={[{ scaleType: 'band', data: safeStats.classStats.map(c => `${c.class} (${c.count})`) }]}
          height={300}
          sx={styles.barChart}
        />
      </Box>

      {/* Бар чарт для эмоций */}
      <Box sx={styles.chartContainer}>
        <Typography variant="subtitle1" sx={styles.chartTitle}>
          Статистика эмоций (кол-во и %)
        </Typography>
        <BarChart
          series={[{ data: safeStats.emotionStats.map(e => e.percentage) }]}
          xAxis={[{ scaleType: 'band', data: safeStats.emotionStats.map(e => `${e.emotion} (${e.count})`) }]}
          height={300}
          sx={styles.barChart}
        />
      </Box>

      {/* Прогресс бар для наложений */}
      <Box sx={styles.progressItem}>
        <Typography variant="subtitle2" sx={styles.statText}>
          Процент наложений речи
        </Typography>
        <LinearProgress
          variant="determinate"
          value={safeStats.overlapDetails.percentage}
          sx={{
            ...styles.progressBar,
            '& .MuiLinearProgress-bar': { backgroundColor: '#ff9800' },
          }}
        />
        <Typography variant="body2" sx={styles.statText2}>
          {safeStats.overlapDetails.percentage}%
        </Typography>
      </Box>

      {/* Таблица с деталями наложений */}
      <Box sx={styles.chartContainer}>
        <Typography variant="subtitle1" sx={styles.chartTitle}>
          Детали наложений
        </Typography>
        <Table sx={{ minWidth: 650 }} aria-label="overlap table">
          <TableHead>
            <TableRow>
              <TableCell>Начало</TableCell>
              <TableCell>Конец</TableCell>
              <TableCell>Длительность</TableCell>
              <TableCell>Спикеры</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {safeStats.overlapDetails.intervals.map((interval, index) => (
              <TableRow key={index}>
                <TableCell>{formatTime(interval.start_ms)}</TableCell>
                <TableCell>{formatTime(interval.end_ms)}</TableCell>
                <TableCell>{formatTime(interval.duration_ms)}</TableCell>
                <TableCell>{interval.speakers.map(id => `Спикер ${id}`).join(', ')}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <Typography variant="body2" sx={{ mt: 2 }}>
          Общее количество наложений: {safeStats.overlapDetails.count}
        </Typography>
        <Typography variant="body2">
          Общее время наложений: {formatTime(safeStats.overlapDetails.total_ms)}
        </Typography>
      </Box>
    </Box>
  );
};

export default StatsPanel;