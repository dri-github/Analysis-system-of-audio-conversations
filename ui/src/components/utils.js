// Функция для форматирования длительности в "HH:MM:SS"
export const formatDuration = (totalSeconds) => {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

// Функция для определения стороны и стиля по спикеру
export const getSpeakerStyle = (speakerId) => {
  const isSpeakerZero = speakerId === 0;
  return {
    justifyContent: isSpeakerZero ? 'flex-end' : 'flex-start',
    flexDirection: isSpeakerZero ? 'row-reverse' : 'row',
    ml: isSpeakerZero ? 'auto' : 0,
    mr: isSpeakerZero ? 0 : 'auto',
  };
};

// Функция для цвета по классу (с базовым оттенком по спикеру)
export const getClassColor = (fragment) => {
  const className = fragment.classifiers?.smc?.["Скрипты1"]?.classes?.[0]?.class || "N/A";
  const colorMap = {
    "Приветствие": "#53d653ff",
    "Общие вопросы": "#53a5e0ff",
    "Запрос информации": "#d0963aff",
    "Жалоба": "#f44d66ff",
    "Возражения клиента": "#bf70cbff",
    "Завершение разговора": "#e65e5eff",
    "Оператор": "#3fbaf3ff",
    "N/A": "#fa8888",
  };
  let baseColor = colorMap[className] || "#fafafa";

  const speakerId = fragment.speaker;
  if (speakerId === 0) {
    baseColor = baseColor === "#e8f5e8" ? '#e1f5fe' : baseColor;
  } else {
    baseColor = baseColor === "#e1f5fe" ? '#f0f0f0' : baseColor;
  }

  return baseColor;
};

// Функция для извлечения класса
export const getClassLabel = (fragment) => {
  const classifiers = fragment.classifiers?.smc?.["Оценка_разговора_1"]?.classes;
  if (classifiers && classifiers.length > 0) {
    const firstClass = classifiers[0];
    return `${firstClass.class} (confidence: ${firstClass.confidence.toFixed(2)})`;
  }
  return "N/A";
};

// Функция для извлечения эмоции
export const getEmotionLabel = (fragment) => {
  const emotion = fragment.voice_analysis?.emotion;
  if (emotion && emotion.class) {
    return `${emotion.class} (confidence: ${emotion.confidence.toFixed(2)})`;
  }
  return "N/A";
};

// Функция для топ эмоции
export const getTopEmotion = (fragments) => {
  const emotionCount = fragments.reduce((acc, fragment) => {
    const emotion = fragment.voice_analysis?.emotion?.class || 'N/A';
    acc[emotion] = (acc[emotion] || 0) + 1;
    return acc;
  }, {});
  return Object.keys(emotionCount).reduce((a, b) => emotionCount[a] > emotionCount[b] ? a : b, 'N/A');
};

// Функция для топ класса
export const getTopClass = (fragments) => {
  const classCount = fragments.reduce((acc, fragment) => {
    const className = fragment.classifiers?.smc?.["Оценка_разговора_1"]?.classes?.[0]?.class || 'N/A';
    acc[className] = (acc[className] || 0) + 1;
    return acc;
  }, {});
  return Object.keys(classCount).reduce((a, b) => classCount[a] > classCount[b] ? a : b, 'N/A');
};
