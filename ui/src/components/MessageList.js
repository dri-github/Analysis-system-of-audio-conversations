import React from 'react';
import { Box, Typography, List } from '@mui/material';
import { styles } from './styles';
import { getClassLabel } from './utils';
import MessageItem from './MessageItem';

const MessageList = ({ fragments, searchTerm, selectedClass }) => {
  // Фильтрация фрагментов
  const filteredFragments = (fragments && Array.isArray(fragments) ? fragments : []).filter(fragment => {
    const matchesSearch = fragment.text.toLowerCase().includes(searchTerm.toLowerCase());
    const fragmentClass = getClassLabel(fragment).split(' (')[0] || 'N/A';
    const matchesClass = selectedClass === 'Все' || fragmentClass === selectedClass;
    return matchesSearch && matchesClass;
  });

  return (
    <Box>
      {filteredFragments.length > 0 ? (
        <List sx={styles.messageList}>
          {filteredFragments.map((fragment, fragIndex) => (
            <MessageItem key={fragIndex} fragment={fragment} />
          ))}
        </List>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
          Фрагменты не найдены по текущим фильтрам.
        </Typography>
      )}
    </Box>
  );
};

export default MessageList;