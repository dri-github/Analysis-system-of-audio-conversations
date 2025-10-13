export const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    width: '80%',
    maxWidth: '1400px',
    margin: '0 auto',
    marginTop: '10px',
    minHeight: '100vh', // minHeight вместо height, чтобы мог расти
    backgroundColor: '#f5f5f5',
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    overflowY: 'auto', // Скролл для всей страницы, если контент больше экрана
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    minHeight: 0, // Важно для flex в overflow-контейнере
  },
  analysisHeader: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: 2,
    borderTopLeftRadius: 10,
    borderTopRightRadius: 10,
    borderBottomRightRadius: 0,
    borderBottomLeftRadius: 0,
    marginBottom: 2,
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    '& h5': {
      marginBottom: 0.5,
    },
    flexShrink: 0,
  },
  leftPanel: {
    width: '25%',
    borderRight: '1px solid #e0e0e0',
    backgroundColor: '#fff',
    overflowY: 'auto', // Скролл для вкладок, если много
    flexShrink: 0,
  },
  rightPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    py: 3,
    px: 2,
    boxShadow: 'inset -2px 0 8px rgba(0,0,0,0.05)',
    boxSizing: 'border-box',
    minHeight: 0, // Важно для flex
  },
  fixedSection: {
    flexShrink: 0,
    backgroundColor: '#f5f5f5',
    padding: 2,
    borderBottom: '1px solid #e0e0e0',
  },
  filterControls: {
    display: 'flex',
    gap: 2,
    alignItems: 'center',
    marginTop: 2,
  },
  tabs: {
    borderRight: 1,
    borderColor: 'divider',
    '& .MuiTab-root': {
      alignItems: 'flex-start',
    },
  },
  tab: {
    textTransform: 'none',
    justifyContent: 'flex-start',
    minWidth: 'auto',
    fontSize: '1.3rem',
  },
  statsPanel: {
    p: 2,
    mb: 2,
    borderRadius: 2,
    boxShadow: 1,
    backgroundColor: '#fff',
  },

  messageList: {
    bgcolor: 'background.paper',
    width: '100%',
    flex: 1, // Заполняет доступное пространство
    overflowY: 'auto', // Независимый скролл списка
    maxHeight: 'none', // Убираем ограничение, если было
  },
  scrollableSection: { // Используй этот стиль для Box вокруг MessageList в ConversationPage
    flex: 1,
    display: 'flex',
    overflow: 'hidden', // Скрываем скролл здесь, передаем в List
  },
  progressContainer: {
    display: 'flex',
    gap: 2,
    mb: 2,
    justifyContent: 'space-between',
    flexWrap: 'wrap',
  },
  progressItem: {
    flex: 1,
    minWidth: 150,
    textAlign: 'center',
    transition: 'all 0.3s ease',
    '&:hover': {
      transform: 'scale(1.02)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    },
  },
  progressBar: {
    height: 30,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
    '& .MuiLinearProgress-bar': {
      borderRadius: 8,
      transition: 'transform 0.6s ease-out',
    },
    operatorBar: {
      background: 'linear-gradient(90deg, #199f1dff 0%, #13e11eff 100%)',
    },
    clientBar: {
      background: 'linear-gradient(90deg, #276ba2ff 0%, #64b5f6 100%)',
    },
  },
  statText: {
    fontSize: '1.7rem',
    fontWeight: 500,
    lineHeight: 1.2,
    marginTop: 0.5,
    marginBottom: 0.5,
  },
  statText2: {
    fontSize: '2rem',
    fontWeight: 600,
    lineHeight: 1.2,
    marginTop: 1,
  },
  statsGrid: { // Для избежания дубликата
   display: 'flex',
    gap: 2,
    mb: 2,
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    padding: 1,
    backgroundColor: '#ffffff',
    borderRadius: 4,
    boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
    '& > *': {
      
      
      alignItems: 'center',
      paddingLeft: '3rem',
      paddingRight: '3rem',
      fontSize: '1.7rem',
      '& strong': {
        color: '#000000ff',
        marginRight: 1,
      },
    },
  },
};