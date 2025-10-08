import React from 'react';
import { ListItem, Box, Typography } from '@mui/material';
import { getSpeakerStyle, getClassColor, getClassLabel, getEmotionLabel } from './utils';
import { styles } from './styles';

const MessageItem = ({ fragment }) => {
  const style = getSpeakerStyle(fragment.speaker);
  const bgColor = getClassColor(fragment);

  return (
    <ListItem
      alignItems="flex-start"
      sx={{
        ...style,
        mb: 2,
        width: '100%',
        justifyContent: 'stretch',
      }}
    >
      <Box
        sx={{
          p: 2,
          borderRadius: 2,
          width: 'auto',
          flex: 1,
          maxWidth: '80%',
          wordBreak: 'break-word',
          backgroundColor: bgColor,
          borderLeft: `3px solid ${bgColor === "#fafafa" ? "#ccc" : bgColor}`,
          boxShadow: 1,
          transition: 'box-shadow 0.2s ease',
          '&:hover': { boxShadow: 3 },
        }}
      >
        <Typography variant="body1" fontWeight="bold" gutterBottom color='white'>
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
};

export default MessageItem;