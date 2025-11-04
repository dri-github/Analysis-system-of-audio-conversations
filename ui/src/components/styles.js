
export const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    width: '80%',
    maxWidth: '1400px',
    margin: '0 auto',
    marginTop: '10px',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
    overflowY: 'auto',
    boxSizing: 'border-box',
    '@media (max-width: 600px)': {
      width: '100%',
      marginTop: 0,
      borderRadius: 0,
    },
  },
  analysisHeader: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: 2,
    borderTopLeftRadius: 10,
    borderTopRightRadius: 10,
    marginBottom: 2,
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    textAlign: 'center',
    flexShrink: 0,
    '& h5': {
      marginBottom: 0.5,
      fontSize: '2rem',
      color: '#fff',
    },
    '& .MuiTypography-subtitle1': {
      fontSize: '1rem',
      color: '#fff',
    },
    '@media (max-width: 600px)': {
      padding: 1,
      '& h5': {
        fontSize: '1.5rem',
      },
      '& .MuiTypography-subtitle1': {
        fontSize: '0.9rem',
      },
    },
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    minHeight: 0,
    '@media (max-width: 600px)': {
      flexDirection: 'column',
    },
  },
  leftPanel: {
    width: '25%',
    minWidth: '200px',
    borderRight: '1px solid #e0e0e0',
    backgroundColor: '#fff',
    overflowY: 'auto',
    flexShrink: 0,
    '@media (max-width: 600px)': {
      width: '100%',
      minWidth: 'auto',
      maxHeight: '30vh',
    },
  },
  rightPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    py: 3,
    px: 2,
    boxShadow: 'inset -2px 0 8px rgba(0,0,0,0.05)',
    boxSizing: 'border-box',
    minHeight: 0,
    maxWidth: '100%', // Ограничиваем ширину для предотвращения выхода за экран
    overflowX: 'hidden', // Предотвращаем горизонтальный скролл на уровне панели
    '@media (max-width: 600px)': {
      py: 2,
      px: 1,
      overflowX: 'hidden',
    },
  },
  fixedSection: {
    flexShrink: 0,
    backgroundColor: '#f5f5f5',
    padding: 2,
    borderBottom: '1px solid #e0e0e0',
    maxWidth: '100%', // Ограничиваем ширину fixedSection
    '@media (max-width: 600px)': {
      padding: 1,
    },
  },
  scrollableSection: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden',
    '@media (max-width: 600px)': {
      overflowY: 'auto',
    },
  },
  filterControls: {
    display: 'flex',
    gap: 2,
    alignItems: 'center',
    marginTop: 2,
    maxWidth: '100%', // Предотвращаем выход за пределы
    flexWrap: 'wrap', // Переносим элементы на следующую строку
    '@media (max-width: 600px)': {
      flexDirection: 'column',
      gap: 1,
      marginTop: 1,
    },
  },
  tabs: {
    borderRight: 1,
    borderColor: 'divider',
    '& .MuiTab-root': {
      alignItems: 'flex-start',
      fontSize: '1.5rem',
      textTransform: 'none',
      justifyContent: 'flex-start',
      minWidth: 'auto',
      color: '#333',
      '&.Mui-selected': {
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        color: '#667eea',
      },
    },
    '@media (max-width: 600px)': {
      '& .MuiTab-root': {
        fontSize: '1.2rem',
      },
    },
  },
  statsPanel: {
    padding: 3,
    marginBottom: 3,
    borderRadius: 4,
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    backgroundColor: '#fff',
    overflowY: 'auto',
    overflowX: 'auto',
    maxHeight: '80vh',
    width: '100%',
    maxWidth: '100%', // Ограничиваем ширину
    boxSizing: 'border-box',
    '@media (max-width: 600px)': {
      padding: 2,
      maxHeight: '70vh',
      fontSize: '0.9rem',
    },
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: 2,
    marginBottom: 3,
    padding: 2,
    backgroundColor: '#f9f9f9',
    borderRadius: 4,
    boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)',
    maxWidth: '100%', // Ограничиваем ширину
    '& > *': {
      fontSize: '1.1rem',
      '& strong': {
        color: '#333',
        marginRight: 1,
      },
    },
    '@media (max-width: 600px)': {
      gridTemplateColumns: '1fr',
      fontSize: '1rem',
    },
  },
  chartContainer: {
    marginBottom: 4,
    padding: 2,
    borderRadius: 4,
    backgroundColor: '#f9f9f9',
    boxShadow: '0 2px 6px rgba(0,0,0,0.05)',
    maxWidth: '100%', // Ограничиваем ширину
    '@media (max-width: 600px)': {
      padding: 1,
      marginBottom: 2,
    },
  },
  chartTitle: {
    fontSize: '1.4rem',
    fontWeight: 600,
    marginBottom: 1,
    color: '#444',
    '@media (max-width: 600px)': {
      fontSize: '1.2rem',
    },
  },
  barChart: {
    maxWidth: '100%', // Ограничиваем ширину чартов
    '& .MuiChartsAxis-label': {
      fontSize: '0.9rem',
    },
    '& .MuiChartsLegend-series text': {
      fontSize: '1rem',
    },
    '@media (max-width: 600px)': {
      '& .MuiChartsAxis-label': {
        fontSize: '0.8rem',
      },
      '& .MuiChartsLegend-series text': {
        fontSize: '0.9rem',
      },
    },
  },
  progressItem: {
    flex: 1,
    minWidth: 200,
    textAlign: 'left',
    transition: 'all 0.3s ease',
    maxWidth: '100%', // Ограничиваем ширину
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    },
    '@media (max-width: 600px)': {
      minWidth: 150,
    },
  },
  progressBar: {
    height: 12,
    borderRadius: 6,
    backgroundColor: '#e0e0e0',
    maxWidth: '100%', // Ограничиваем ширину
    '& .MuiLinearProgress-bar': {
      borderRadius: 6,
      transition: 'width 0.5s ease-in-out',
    },
    '@media (max-width: 600px)': {
      height: 10,
    },
  },
  statText: {
    fontSize: '1.2rem',
    fontWeight: 500,
    marginBottom: 0.5,
    color: '#555',
    '@media (max-width: 600px)': {
      fontSize: '1rem',
    },
  },
  statText2: {
    fontSize: '1.5rem',
    fontWeight: 600,
    marginTop: 0.5,
    color: '#ff9800',
    '@media (max-width: 600px)': {
      fontSize: '1.3rem',
    },
  },
  table: {
    maxWidth: '100%', // Ограничиваем ширину таблицы
    '& .MuiTableCell-head': {
      fontWeight: 600,
      backgroundColor: '#f5f5f5',
      color: '#333',
    },
    '& .MuiTableCell-body': {
      fontSize: '0.9rem',
    },
    '@media (max-width: 600px)': {
      '& .MuiTableCell-head': {
        fontSize: '0.8rem',
      },
      '& .MuiTableCell-body': {
        fontSize: '0.8rem',
      },
    },
  },
  messageList: {
    backgroundColor: '#fff',
    width: '100%',
    flex: 1,
    overflowY: 'auto',
    maxWidth: '100%', // Ограничиваем ширину
    '@media (max-width: 600px)': {
      maxHeight: '50vh',
    },
  },
};
