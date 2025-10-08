# Analysis-system-of-audio-conversations 

## Backend for Python:
- POST /api/conversations?fname={file_name}&fpath={file_path} (JSON передается в теле) - добавление JSON отпаршеного разговора в БД
- GET  /api/conversations - возвращает полный список всех разговоров
- GET  /api/conversations/{id} - возвращает конкретный JSON разговора

- ??? GET  /analyze/stats - возвращает JSON со статистикой (это под вопросом, примера данных не дали)

## Frontend for React:
- GET  /analyze - основная HTML страница (можно сделать либо, отображение страницы но без подробностей с открытым заранее списком или сделать чтобы открывался последний добавленный диалог)
- GET  /analyze?id={speak_id} - как и запрос выше, только для выбранного разговора

<img width="548" height="435" alt="image" align="center" src="https://github.com/user-attachments/assets/3fa8e4c8-87a6-489d-b2c2-f3d703f524d6" />
