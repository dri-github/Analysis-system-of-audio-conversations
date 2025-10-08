import React from 'react';
import { Box, Typography, List, Divider, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { styles } from './styles';
import { getClassLabel } from './utils';
import MessageItem from './MessageItem';

const MessageList = ({ fragments, searchTerm, setSearchTerm, selectedClass, setSelectedClass }) => {
  // Извлечение уникальных классов для dropdown
  const uniqueClasses = Array.from(new Set(fragments && Array.isArray(fragments) ? fragments.map(fragment => getClassLabel(fragment).split(' (')[0] || 'N/A') : []));

  // Фильтрация фрагментов
  const filteredFragments = (fragments && Array.isArray(fragments) ? fragments : []).filter(fragment => {
    const matchesSearch = fragment.text.toLowerCase().includes(searchTerm.toLowerCase());
    const fragmentClass = getClassLabel(fragment).split(' (')[0] || 'N/A';
    const matchesClass = selectedClass === 'Все' || fragmentClass === selectedClass;
    return matchesSearch && matchesClass;
  });

  // Подсчёт спикеров (с защитой от undefined)
  const speakerCount = fragments && fragments.length > 0 && fragments[0].speakers ? fragments[0].speakers.length : 0;

  return (
    <Box>
      

      <Box sx={styles.filterControls}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Поиск по словам..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          size="small"
          sx={{ flex: 1 }}
        />
        <FormControl variant="outlined" size="small" sx={{ minWidth: 150, ml: 2 }}>
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