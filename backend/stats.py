"""
Модуль для вычисления статистики разговоров из file_data
"""
from typing import Dict, Any, List
from collections import defaultdict, Counter


def calculate_stats(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Вычисляет статистику разговора из file_data
    
    Args:
        file_data: JSON данные разговора
        
    Returns:
        Словарь со статистикой
    """
    if not file_data or "splitted" not in file_data:
        return _empty_stats()
    
    fragments = file_data.get("splitted", [])
    if not fragments:
        return _empty_stats()
    
    # Инициализация счетчиков
    speaker_stats = defaultdict(lambda: {
        "durationMs": 0,
        "fragments": 0,
        "age": None,
        "gender": None
    })
    class_counter = Counter()
    emotion_counter = Counter()
    total_duration_ms = 0
    overlaps = []
    
    # Обработка фрагментов
    for fragment in fragments:
        speaker_id = fragment.get("speaker", 0)
        start_ms = _time_to_ms(fragment.get("start", "0:0:0"))
        stop_ms = _time_to_ms(fragment.get("stop", "0:0:0"))
        duration_ms = stop_ms - start_ms
        
        # Статистика по спикерам
        speaker_stats[speaker_id]["durationMs"] += duration_ms
        speaker_stats[speaker_id]["fragments"] += 1
        
        # Получение возраста и пола из первого фрагмента спикера
        if speaker_stats[speaker_id]["age"] is None:
            voice_analysis = fragment.get("voice_analysis", {})
            speaker_stats[speaker_id]["age"] = voice_analysis.get("age", "unknown")
            speaker_stats[speaker_id]["gender"] = voice_analysis.get("gender", "unknown")
        
        total_duration_ms += duration_ms
        
        # Классы
        classifiers = fragment.get("classifiers", {})
        smc = classifiers.get("smc", {})
        скрипты = smc.get("Скрипты1", {})
        classes = скрипты.get("classes", [])
        if classes:
            class_name = classes[0].get("class", "N/A")
            class_counter[class_name] += 1
        
        # Эмоции
        emotion = fragment.get("emotion")
        if emotion and isinstance(emotion, dict):
            emotion_name = list(emotion.keys())[0] if emotion else "N/A"
            emotion_counter[emotion_name] += 1
        elif isinstance(emotion, str):
            emotion_counter[emotion] += 1
        else:
            voice_emotion = fragment.get("voice_analysis", {}).get("emotion", {})
            if voice_emotion:
                emotion_name = voice_emotion.get("class", "N/A")
                emotion_counter[emotion_name] += 1
    
    # Вычисление наложений (упрощенная версия)
    overlaps = _calculate_overlaps(fragments)
    
    # Форматирование статистики спикеров
    speaker_count = len(speaker_stats)
    speaker_stats_list = []
    for speaker_id, stats in sorted(speaker_stats.items()):
        percentage = (stats["durationMs"] / total_duration_ms * 100) if total_duration_ms > 0 else 0
        speaker_stats_list.append({
            "id": speaker_id,
            "durationMs": stats["durationMs"],
            "percentage": round(percentage, 1),
            "age": stats["age"] or "unknown",
            "gender": stats["gender"] or "unknown",
            "fragments": stats["fragments"]
        })
    
    # Форматирование статистики классов
    total_fragments = len(fragments)
    class_stats_list = []
    for class_name, count in class_counter.most_common():
        percentage = (count / total_fragments * 100) if total_fragments > 0 else 0
        class_stats_list.append({
            "class": class_name,
            "count": count,
            "percentage": round(percentage, 1)
        })
    
    # Форматирование статистики эмоций
    emotion_stats_list = []
    for emotion_name, count in emotion_counter.most_common():
        percentage = (count / total_fragments * 100) if total_fragments > 0 else 0
        emotion_stats_list.append({
            "emotion": emotion_name,
            "count": count,
            "percentage": round(percentage, 1)
        })
    
    # Вычисление наложений
    overlap_count = len(overlaps)
    overlap_total_ms = sum(overlap["duration_ms"] for overlap in overlaps)
    overlap_percentage = (overlap_total_ms / total_duration_ms * 100) if total_duration_ms > 0 else 0
    
    # Средняя длительность фрагмента
    avg_fragment_duration = (total_duration_ms / total_fragments / 1000) if total_fragments > 0 else 0
    
    # Топ эмоция и класс
    top_emotion = emotion_counter.most_common(1)[0][0] if emotion_counter else "N/A"
    top_class = class_counter.most_common(1)[0][0] if class_counter else "N/A"
    
    return {
        "totalDuration": _ms_to_time_string(total_duration_ms),
        "totalDurationMs": total_duration_ms,
        "speakerCount": speaker_count,
        "avgFragmentDuration": round(avg_fragment_duration, 1),
        "topEmotion": top_emotion,
        "topClass": top_class,
        "overlapDetails": {
            "count": overlap_count,
            "total_ms": overlap_total_ms,
            "percentage": round(overlap_percentage, 2),
            "intervals": overlaps
        },
        "speakerStats": speaker_stats_list,
        "classStats": class_stats_list,
        "emotionStats": emotion_stats_list
    }


def _time_to_ms(time_str: str) -> int:
    """Конвертирует строку времени 'HH:MM:SS.mmm' в миллисекунды"""
    try:
        parts = time_str.split(":")
        hours = int(parts[0]) if len(parts) > 0 else 0
        minutes = int(parts[1]) if len(parts) > 1 else 0
        seconds_parts = parts[2].split(".") if len(parts) > 2 else ["0"]
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        
        return (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
    except (ValueError, IndexError):
        return 0


def _ms_to_time_string(ms: int) -> str:
    """Конвертирует миллисекунды в строку формата 'HH:MM:SS'"""
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _calculate_overlaps(fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Вычисляет наложения речи между спикерами
    Упрощенная версия - ищет пересечения временных интервалов
    """
    overlaps = []
    
    # Сортируем фрагменты по времени начала
    sorted_fragments = sorted(fragments, key=lambda f: _time_to_ms(f.get("start", "0:0:0")))
    
    for i, frag1 in enumerate(sorted_fragments):
        start1 = _time_to_ms(frag1.get("start", "0:0:0"))
        stop1 = _time_to_ms(frag1.get("stop", "0:0:0"))
        speaker1 = frag1.get("speaker", 0)
        
        for j, frag2 in enumerate(sorted_fragments[i + 1:], start=i + 1):
            start2 = _time_to_ms(frag2.get("start", "0:0:0"))
            stop2 = _time_to_ms(frag2.get("stop", "0:0:0"))
            speaker2 = frag2.get("speaker", 0)
            
            # Пропускаем, если это тот же спикер
            if speaker1 == speaker2:
                continue
            
            # Проверяем пересечение интервалов
            overlap_start = max(start1, start2)
            overlap_end = min(stop1, stop2)
            
            if overlap_start < overlap_end:
                # Есть наложение
                duration_ms = overlap_end - overlap_start
                overlaps.append({
                    "start_ms": overlap_start,
                    "end_ms": overlap_end,
                    "duration_ms": duration_ms,
                    "speakers": sorted([speaker1, speaker2])
                })
    
    return overlaps


def _empty_stats() -> Dict[str, Any]:
    """Возвращает пустую статистику"""
    return {
        "totalDuration": "00:00:00",
        "totalDurationMs": 0,
        "speakerCount": 0,
        "avgFragmentDuration": 0,
        "topEmotion": "N/A",
        "topClass": "N/A",
        "overlapDetails": {
            "count": 0,
            "total_ms": 0,
            "percentage": 0,
            "intervals": []
        },
        "speakerStats": [],
        "classStats": [],
        "emotionStats": []
    }

