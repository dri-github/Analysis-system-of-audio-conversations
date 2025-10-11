import React, { useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';
import { LinearProgress } from '@mui/material';
import { formatDuration, getTopEmotion, getTopClass } from './utils';
import { styles } from './styles';


const StatsPanel = ({ conversation, fragments }) => {
  const stats = useMemo(() => {
    if (!fragments || !Array.isArray(fragments) || fragments.length === 0 || !conversation) {
      return {
        totalDuration: '00:00:00',
        speakerCount: 0,
        avgDuration: 0,
        topEmotion: 'Не определено',
        topClass: 'Не определено',
        operatorTime: 0,
        clientTime: 0,
      };
    }

    let operatorSeconds = 0;
    let clientSeconds = 0;
    fragments.forEach(f => {
      const [hours, minutes, seconds] = f.duration.split(':').map(Number);
      const dur = hours * 3600 + minutes * 60 + seconds;
      if (f.speaker === 0) {
        operatorSeconds += dur;
      } else {
        clientSeconds += dur;
      }
    });
    const totalSeconds = operatorSeconds + clientSeconds;
    const operatorPercent = totalSeconds > 0 ? (operatorSeconds / totalSeconds * 100).toFixed(2) : 0;
    const clientPercent = totalSeconds > 0 ? (clientSeconds / totalSeconds * 100).toFixed(2) : 0;

    const durations = fragments.map(f => {
      const [hours, minutes, seconds] = f.duration.split(':').map(Number);
      return hours * 3600 + minutes * 60 + seconds;
    });
    const totalDur = durations.reduce((sum, d) => sum + d, 0);
    const avgSeconds = totalDur / fragments.length || 0;

    return {
      totalDuration: formatDuration(totalDur),
      speakerCount: conversation.speakers ? conversation.speakers.length : 0,
      avgDuration: avgSeconds.toFixed(2),
      topEmotion: getTopEmotion(fragments) || 'Не определено',
      topClass: getTopClass(fragments) || 'Не определено',
      operatorTime: parseFloat(operatorPercent),
      clientTime: parseFloat(clientPercent),
    };
  }, [conversation.speakers, fragments]);

  return (
    <Box sx={styles.statsPanel}>
      <Typography variant="h6" gutterBottom sx={{ fontSize: '2rem' }}>Статистика разговора</Typography>
      
      {/* Графики: Два progress bars с улучшенными стилями */}
      <Box sx={styles.progressContainer}>
        <Box sx={styles.progressItem}>
          <Typography variant="subtitle2" color="#000000ff" sx={styles.statText}>
            Время работы оператора
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={stats.operatorTime} 
            sx={{
              ...styles.progressBar,
              '& .MuiLinearProgress-bar': { ...styles.progressBar.operatorBar },
            }} 
          />
          <Typography variant="body2" sx={{ ...styles.statText2, color: '#13e11eff' }}>
            {stats.operatorTime}%
          </Typography>
        </Box>
        
        <Box sx={styles.progressItem}>
          <Typography variant="subtitle2" color="#000000ff" sx={styles.statText}>
            Время работы клиента
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={stats.clientTime} 
            sx={{
              ...styles.progressBar,
              '& .MuiLinearProgress-bar': { ...styles.progressBar.clientBar },
            }} 
          />
          <Typography variant="body2" sx={{ ...styles.statText2, color: '#2196f3' }}>
            {stats.clientTime}%
          </Typography>
        </Box>
      </Box>

      {/* Остальная статистика */}
     <Box sx={styles.statsGrid}>
        <Typography><strong>Общее время:</strong> {stats.totalDuration}</Typography>
        <Typography><strong>Спикеров:</strong> {stats.speakerCount}</Typography>
        <Typography><strong>Топ эмоция:</strong> {stats.topEmotion}</Typography>
        <Typography><strong>Топ класс:</strong> {stats.topClass}</Typography>
      </Box>
    </Box>
  );
};

export default StatsPanel;