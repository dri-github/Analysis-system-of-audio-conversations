import React from 'react';
import { Box, Typography, List } from '@mui/material';
import { styles } from './styles';
import { getClassLabel } from './utils';
import MessageItem from './MessageItem';

const MessageList = ({ fragments, searchTerm, selectedClass, onSeekAudio }) => {
  // Фильтрация фрагментов
  const filteredFragments = (fragments && Array.isArray(fragments) ? fragments : []).filter(fragment => {
    const matchesSearch = fragment.text.toLowerCase().includes(searchTerm.toLowerCase());
    const fragmentClass = getClassLabel(fragment).split(' (')[0] || 'N/A';
    const matchesClass = selectedClass === 'Все' || fragmentClass === selectedClass;
    return matchesSearch && matchesClass;
  });

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', height: '1000px' }}>
      {filteredFragments.length > 0 ? (
        <List sx={{ ...styles.messageList, flex: 1, overflowY: 'scroll' }}>
          {filteredFragments.map((fragment, fragIndex) => (
            <MessageItem key={fragIndex} fragment={fragment} onSeekAudio={onSeekAudio} />
          ))}
        </List>
      ) : (
        <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Фрагменты не найдены по текущим фильтрам.
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default MessageList;