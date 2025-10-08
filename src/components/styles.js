export const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column', // Изменяем на вертикальный стек
    width: '80%',
    maxWidth: '1200px',
    margin: '0 auto',
    height: '100vh',
    backgroundColor: '#f5f5f5',
    borderTopLeftRadius: 12,    // Скругление верхнего левого угла
    borderTopRightRadius: 12,   // Скругление верхнего правого угла
    

  },
  mainContent: {
    display: 'flex',
    flex: 1, // Занимает оставшееся пространство
    overflow: 'hidden', // Предотвращает переполнение
  },
  analysisHeader: {
    backgroundColor: '#f5f5f5',
    padding: 2,
    borderTopLeftRadius: 4,    // Скругление верхнего левого угла
    borderTopRightRadius: 4,   // Скругление верхнего правого угла
    borderBottomRightRadius: 0, // Меньше скругление нижнего правого угла
    borderBottomLeftRadius: 0,
    marginBottom: 2,
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    '& h5': {
      marginBottom: 0.5,
    },
  },
  leftPanel: {
    width: '25%',
    borderRight: '1px solid #e0e0e0',
    overflowY: 'auto',
    
  },
  rightPanel: {
    flex: 1,
    padding: 2,
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
  },
  rightPanel: {
    width: '70%',
    py: 3,
    px: 2,
    overflowY: 'auto',
    boxShadow: 'inset -2px 0 8px rgba(0,0,0,0.05)',
    boxSizing: 'border-box',
  },
  statsPanel: {
    p: 2,
    mb: 2,
    borderRadius: 2,
    boxShadow: 1,
    backgroundColor: '#fff',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 1,
  },
  filterControls: {
    display: 'flex',
    gap: 2,
    mb: 2,
    alignItems: 'center',
  },
  messageList: {
    bgcolor: 'background.paper',
    width: '100%',
  },
  progressContainer: {
    display: 'flex',
    gap: 2,
    mb: 2,
    justifyContent: 'space-between',
    flexWrap: 'wrap', // Адаптивность для маленьких экранов
  },
  progressItem: {
    flex: 1,
    minWidth: 150, // Минимальная ширина для читаемости
    textAlign: 'center',
    transition: 'all 0.3s ease', // Плавная анимация при изменении размеров
    '&:hover': {
      transform: 'scale(1.02)', // Лёгкое увеличение при наведении
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)', // Тень при ховере
    },
  },
  progressBar: {
    height: 30, // Увеличенная высота для акцента
    borderRadius: 8, // Скругление углов
    backgroundColor: '#f0f0f0', // Светлый фон для контраста
    '& .MuiLinearProgress-bar': {
      borderRadius: 8,
      transition: 'transform 0.6s ease-out', // Плавная анимация заполнения
    },
    operatorBar: {
      background: 'linear-gradient(90deg, #199f1dff 0%, #13e11eff 100%)', // Градиент зелёного
    },
    clientBar: {
      background: 'linear-gradient(90deg, #276ba2ff 0%, #64b5f6 100%)', // Градиент синего
    },
  },
  statText: { // Новый стиль для текста рядом с прогресс-барами
    fontSize: '1.7rem', // Увеличение базового размера текста (по умолчанию ~1rem = 16px)
    fontWeight: 500, // Средняя жирность для акцента
    lineHeight: 1.2, // Улучшенная читаемость
    marginTop: 0.5, // Отступ сверху для баланса
    marginButtom:0.5,
  },
  statText2: { // Новый стиль для текста рядом с прогресс-барами
    fontSize: '2rem', // Увеличение базового размера текста (по умолчанию ~1rem = 16px)
    fontWeight: 600, // Средняя жирность для акцента
    lineHeight: 1.2, // Улучшенная читаемость
    marginTop: 1, // Отступ сверху для баланса
  },
  
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, // 1 колонка на мобильных, 2 на планшетах
    gap: 1.5, // Отступ между элементами
    padding: 1, // Внутренний отступ
    backgroundColor: '#ffffff', // Фон для выделения
    borderRadius: 4, // Скругление углов
    boxShadow: '0 2px 6px rgba(0,0,0,0.2)', // Лёгкая тень
    '& > *': { // Стили для каждого элемента внутри грид
      display: 'flex',
      alignItems: 'center',
      padding: '0rem',
      fontSize:'1.8rem',
      '& strong': {
        color: '#000000ff', // Цвет для акцентов (синий, как у клиента)
        marginRight: 1, // Отступ между bold и значением
      },
    },
  },
};