import re
from gemini_service import GeminiService
from database import Database


class Vocabulary:
    def __init__(self):
        self.gemini = GeminiService()
        self.db = Database()
        self.current_words = {}  # Храним текущие слова для каждого пользователя
    
    def parse_vocabulary_response(self, response, topic):
        """Парсить текстовый ответ от Gemini и извлечь слова"""
        words = []

        word_blocks = re.split(r'СЛОВО\s*\d+\s*:', response, flags=re.IGNORECASE)
        
        for block in word_blocks[1:]:
            if not block.strip():
                continue
            
            try:
                word_data = self.parse_word_block(block)
                if word_data:
                    words.append(word_data)
            except Exception:
                continue
        
        # Если основной метод не сработал, пробуем fallback
        if len(words) < 3:
            words = self.fallback_parse(response)
        
        if words:
            return {
                "topic": topic,
                "words": words
            }
        return None
    
    def parse_word_block(self, block):
        """Парсить отдельный блок слова"""
        lines = block.strip().split('\n')
        
        word = ""
        transcription = ""
        translation = ""
        example_en = ""
        example_ru = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Ищем английское слово
            eng_match = re.match(r'^(?:Английское|English|Word)\s*:\s*(.+)', line, re.IGNORECASE)
            if eng_match:
                word = eng_match.group(1).strip()
                continue
            
            # Ищем транскрипцию
            trans_match = re.match(r'^(?:Транскрипция|Transcription)\s*:\s*(.+)', line, re.IGNORECASE)
            if trans_match:
                transcription = trans_match.group(1).strip()
                continue
            
            # Ищем перевод
            transl_match = re.match(r'^(?:Перевод|Translation)\s*:\s*(.+)', line, re.IGNORECASE)
            if transl_match:
                translation = transl_match.group(1).strip()
                continue
            
            # Ищем пример на английском
            ex_en_match = re.match(r'^(?:Пример EN|Example EN|English example)\s*:\s*(.+)', line, re.IGNORECASE)
            if ex_en_match:
                example_en = ex_en_match.group(1).strip()
                continue
            
            # Ищем пример на русском
            ex_ru_match = re.match(r'^(?:Пример RU|Example RU|Russian example)\s*:\s*(.+)', line, re.IGNORECASE)
            if ex_ru_match:
                example_ru = ex_ru_match.group(1).strip()
                continue
        
        # Проверяем, что у нас есть минимум слово и перевод
        if word and translation:
            return {
                "word": word,
                "transcription": transcription if transcription else "[-]",
                "translation": translation,
                "example_en": example_en if example_en else f"Example with {word}.",
                "example_ru": example_ru if example_ru else ""
            }
        
        return None
    
    def fallback_parse(self, response):
        """Запасной метод парсинга - более гибкий"""
        words = []
        
        # Ищем паттерны типа "слово - перевод" или "слово [транскрипция] - перевод"
        # Паттерн 1: word [transcription] - translation
        pattern1 = r'(\w+)\s*(\[.+?\])?\s*[-–—]\s*([^\n]+)'
        
        matches = re.findall(pattern1, response)
        
        for match in matches:
            if len(match) >= 3:
                word = match[0].strip()
                transcription = match[1].strip() if match[1] else "[-]"
                translation = match[2].strip()
                
                # Фильтруем служебные слова
                if len(word) > 1 and not word.lower() in ['the', 'a', 'an', 'is', 'are']:
                    words.append({
                        "word": word,
                        "transcription": transcription,
                        "translation": translation,
                        "example_en": f"{word.capitalize()} is a useful word.",
                        "example_ru": ""
                    })
        
        # Если паттерн 1 не сработал, ищем списки
        if len(words) < 3:
            # Ищем нумерованные списки: "1. word - translation"
            pattern2 = r'\d+[\.\)]\s*(\w+)\s*[-–—]\s*([^\n]+)'
            matches2 = re.findall(pattern2, response)
            
            for match in matches2:
                if len(match) >= 2:
                    word = match[0].strip()
                    translation = match[1].strip()
                    
                    if len(word) > 1:
                        words.append({
                            "word": word,
                            "transcription": "[-]",
                            "translation": translation,
                            "example_en": f"{word.capitalize()} is a useful word.",
                            "example_ru": ""
                        })
        
        return words
    
    def generate_words(self, topic, number_of_words=10):
        """Сгенерировать слова по теме"""
        response = self.gemini.generate_vocabulary(topic, number_of_words)
        
        # Проверяем на ошибку API
        if response.startswith("GEMINI_ERROR:"):
            return False, response.replace("GEMINI_ERROR: ", "")
        
        # Парсим текстовый ответ
        vocabulary_data = self.parse_vocabulary_response(response, topic)
        
        if vocabulary_data and vocabulary_data.get('words'):
            return True, vocabulary_data
        else:
            return False, f"Не удалось распознать слова. Попробуйте ещё раз. Ответ: {response[:300]}..."
    
    def save_words(self, user_id, vocabulary_data):
        """Сохранить слова в БД"""
        if 'words' in vocabulary_data:
            self.db.save_vocabulary(
                user_id,
                vocabulary_data.get('topic', 'Unknown'),
                vocabulary_data['words']
            )
            self.current_words[user_id] = vocabulary_data
            return True
        return False
    
    def get_current_words(self, user_id):
        """Получить текущие слова пользователя"""
        return self.current_words.get(user_id)
    
    def format_words_for_display(self, vocabulary_data):
        """Форматировать слова для отображения"""
        if not vocabulary_data or 'words' not in vocabulary_data:
            return "Слова не найдены"
        
        text = f"📚 Тема: {vocabulary_data.get('topic', 'Unknown')}\n\n"
        
        for i, word in enumerate(vocabulary_data['words'], 1):
            text += f"{i}. {word.get('word', '')} [{word.get('transcription', '')}]\n"
            text += f"   Перевод: {word.get('translation', '')}\n"
            text += f"   Пример: {word.get('example_en', '')}\n"
            if word.get('example_ru'):
                text += f"   {word.get('example_ru', '')}\n"
            text += "\n"
        
        return text
    
    def format_words_compact(self, vocabulary_data):
        """Компактный формат для отправки (если сообщение слишком длинное)"""
        if not vocabulary_data or 'words' not in vocabulary_data:
            return "Слова не найдены"
        
        text = f"📚 Тема: *{vocabulary_data.get('topic', 'Unknown')}*\n\n"
        
        for i, word in enumerate(vocabulary_data['words'], 1):
            text += f"*{i}.* {word.get('word', '')} [{word.get('transcription', '')}]\n"
            text += f"_{word.get('translation', '')}_\n"
            if word.get('example_en'):
                text += f"🇬🇧 {word.get('example_en', '')}\n"
            if word.get('example_ru'):
                text += f"🇷🇺 {word.get('example_ru', '')}\n"
            text += "\n"
            
            # Если текст становится слишком длинным, делаем разбивку
            if len(text) > 3000:
                remaining = vocabulary_data['words'][i:]
                if remaining:
                    text += f"\n... и ещё {len(remaining)} слов"
                break
        
        return text
    
    def get_user_vocabulary_history(self, user_id):
        """Получить историю изученных слов пользователя"""
        return self.db.get_user_vocabulary(user_id)