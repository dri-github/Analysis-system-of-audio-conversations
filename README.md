# Analysis-system-of-audio-conversations 

SpearekRecognize Service:
- Берёт файл разговора из специальной дирректории
- Создает таску на обработку
- По окончанию обработки загружает JSON файл в БД

Analitics Service:
- Получает GET /analyze - отображает HTML страницу (исходная)
- Получает GET /analyze?id={speak_id} - отображает страницу определённого разговора (аналогично с пунктом выше)
- Получает GET /analyze/stats - возвращает JSON со статистикой

<img width="548" height="435" alt="image" src="https://github.com/user-attachments/assets/3fa8e4c8-87a6-489d-b2c2-f3d703f524d6" />
