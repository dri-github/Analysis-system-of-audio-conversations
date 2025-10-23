import React, { useEffect, useRef } from 'react';
import { ListItem, Box, Typography } from '@mui/material';
import { getSpeakerStyle, getClassColor, getClassLabel, getEmotionLabel } from './utils';
import { styles } from './styles';

const MessageItem = ({ fragment, onSeekAudio }) => {
  const style = getSpeakerStyle(fragment.speaker);
  const bgColor = getClassColor(fragment);

  const handleClick = () => {
    if (onSeekAudio && fragment.start && fragment.stop) {
      onSeekAudio(fragment.start, fragment.stop); // Передаем start и stop
    }
  };

  return (
    <ListItem
      alignItems="flex-start"
      sx={{
        ...style,
        mb: 2,
        width: '80%',
        justifyContent: 'stretch',
        cursor: 'pointer',
      }}
      onClick={handleClick}
    >
      <Box
        sx={{
          p: 2,
          borderRadius: 2,
          borderBottomRightRadius:0.5,
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
        <Typography variant="body1" fontWeight="bold" gutterBottom color='white' sx={{ fontSize: '1.4em' }}>
          {fragment.text}
        </Typography>
        
        <Typography variant="body2" fontWeight="medium" gutterBottom color='white' sx={{ fontSize: '1em' }}>
          {getClassLabel(fragment)} | {getEmotionLabel(fragment)}
        </Typography>
        
        <Typography variant="body2" gutterBottom color='white' sx={{ fontSize: '1em' }}>
          {fragment.start} - {fragment.stop}
        </Typography>
        
        <Typography variant="caption" color='white' sx={{ fontSize: '1rem', opacity: 0.9 }}>
          Спикер {fragment.speaker} 
        </Typography>
      </Box>
    </ListItem>
  );
};

export default MessageItem;