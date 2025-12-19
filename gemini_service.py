import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
    
    def generate_text(self, prompt, system_instruction=None):
        """Генерировать текст с помощью Gemini"""
        try:
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            # Если есть системная инструкция, добавляем её в начало промпта
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            # Проверяем, есть ли текст в ответе
            if response.parts:
                return response.text
            else:
                # Если ответ пустой, возвращаем информативную ошибку
                finish_reason = getattr(response.candidates[0], 'finish_reason', None) if response.candidates else None
                return f"GEMINI_ERROR: Пустой ответ от API. Причина: {finish_reason}"
                
        except Exception as e:
            return f"GEMINI_ERROR: {str(e)}"
    
    def create_grammar_test(self, tense_type="all"):
        """Создать тест по временам английского языка"""
        
        tense_descriptions = {
            "all": "все времена английского языка",
            "present": "Present Simple, Present Continuous, Present Perfect, Present Perfect Continuous",
            "past": "Past Simple, Past Continuous, Past Perfect, Past Perfect Continuous",
            "future": "Future Simple, Future Continuous, Future Perfect, Future Perfect Continuous"
        }
        
        tense_desc = tense_descriptions.get(tense_type, "все времена английского языка")
        
        prompt = f"""Создай тест по английской грамматике на тему: {tense_desc}.

Требования:
1. Тест должен содержать 10 вопросов
2. Каждый вопрос должен иметь 4 варианта ответа (a, b, c, d)
3. Только один вариант ответа правильный
4. Вопросы должны быть разного уровня сложности

Формат вывода - используй ТОЧНО такой текстовый формат для КАЖДОГО вопроса:

ВОПРОС 1:
Текст вопроса здесь
a) первый вариант
b) второй вариант  
c) третий вариант
d) четвертый вариант
ОТВЕТ: a
ОБЪЯСНЕНИЕ: объяснение почему этот ответ правильный

ВОПРОС 2:
...и так далее для всех 10 вопросов.

Начни прямо с "ВОПРОС 1:" без вступления."""
        
        return self.generate_text(prompt)
    
    def generate_vocabulary(self, topic, number_of_words=10):
        """Сгенерировать слова для изучения по теме"""
        
        prompt = f"""Создай список из {number_of_words} английских слов для изучения по теме: "{topic}".

Для КАЖДОГО слова используй ТОЧНО такой текстовый формат:

СЛОВО 1:
Английское: apple
Транскрипция: [ˈæpl]
Перевод: яблоко
Пример EN: I eat an apple every day.
Пример RU: Я ем яблоко каждый день.

СЛОВО 2:
Английское: banana
Транскрипция: [bəˈnænə]
Перевод: банан
Пример EN: Bananas are yellow and sweet.
Пример RU: Бананы желтые и сладкие.

...и так далее для всех {number_of_words} слов.

Важно: начни сразу со "СЛОВО 1:" без вступления. Тема: {topic}"""
        
        return self.generate_text(prompt)
    
    def check_grammar(self, user_text):
        """Проверить грамматику текста пользователя и вернуть исправления"""
        
        prompt = f"""Analyze the following English text for grammar, spelling, and vocabulary errors.

Text to analyze: "{user_text}"

IMPORTANT RULES:
1. DO NOT count punctuation errors (missing periods, commas, apostrophes, etc.)
2. DO NOT count capitalization errors
3. ONLY check for real grammar mistakes, spelling errors, and wrong word usage
4. If the text is grammatically correct but missing punctuation - report 0 errors

Use EXACTLY this format for your response:

ERRORS_FOUND: [number of REAL grammar/spelling errors, use 0 if no errors]
CORRECTED: [corrected version of the text, or "No corrections needed" if perfect]
MISTAKES:
[If there are REAL errors, list each one like this:]
- Original: [wrong part] -> Correct: [right version] | Explanation: [brief explanation in Russian]

[If no errors, write:]
- No mistakes found. Great job!

Example response for text with errors:
ERRORS_FOUND: 2
CORRECTED: I want to buy a red apple.
MISTAKES:
- Original: "wont" -> Correct: "want" | Explanation: Опечатка, "wont" означает "привычка"
- Original: "a apple" -> Correct: "an apple" | Explanation: Перед гласной используется артикль "an"

Example - text "i want apple" has only 1 error (missing article), NOT 2:
ERRORS_FOUND: 1
CORRECTED: I want an apple.
MISTAKES:
- Original: "want apple" -> Correct: "want an apple" | Explanation: Нужен артикль "an" перед существительным

Now analyze the text."""
        
        response = self.generate_text(prompt)
        
        if response.startswith("GEMINI_ERROR:"):
            return {
                'errors_count': 0,
                'corrected_text': user_text,
                'mistakes': [],
                'raw_response': response
            }
        
        # Парсим ответ
        return self._parse_grammar_check(response, user_text)
    
    def _parse_grammar_check(self, response, original_text):
        """Парсить ответ проверки грамматики"""
        result = {
            'errors_count': 0,
            'corrected_text': original_text,
            'mistakes': [],
            'raw_response': response
        }
        
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Ищем количество ошибок
            if line.upper().startswith('ERRORS_FOUND:'):
                try:
                    count = line.split(':')[1].strip()
                    result['errors_count'] = int(count)
                except (ValueError, IndexError):
                    pass
            
            # Ищем исправленный текст
            elif line.upper().startswith('CORRECTED:'):
                corrected = line.split(':', 1)[1].strip() if ':' in line else original_text
                if corrected.lower() != 'no corrections needed':
                    result['corrected_text'] = corrected
            
            # Ищем ошибки
            elif line.startswith('-') and 'Original:' in line and 'Correct:' in line:
                result['mistakes'].append(line)
            elif line.startswith('-') and 'No mistakes' not in line and line != '-':
                result['mistakes'].append(line)
        
        return result
    
    def continue_dialogue(self, conversation_history, user_message, ai_role="seller"):
        """Продолжить диалог в роли продавца или покупателя"""
        
        if ai_role == "seller":
            system_instruction = """You are a friendly shop assistant/seller in a store.
             Your task is to help the customer choose products, answer their questions, and suggest alternatives.

IMPORTANT RULES:
1. Respond ONLY in English
2. Be polite, professional, and helpful
3. Use simple, clear English suitable for language learners
4. Keep responses short (2-4 sentences)
5. Ask follow-up questions to engage the customer"""
            role_label_user = "Customer"
            role_label_ai = "Seller"
        else:
            system_instruction = """You are a customer in a store.
             Your task is to ask about products, inquire about prices and features.

IMPORTANT RULES:
1. Respond ONLY in English
2. Be polite and curious
3. Use simple, clear English suitable for language learners
4. Keep responses short (2-4 sentences)
5. Ask questions about products you're interested in"""
            role_label_user = "Seller"
            role_label_ai = "Customer"
        
        # Формируем контекст диалога
        conversation_text = ""
        for msg in conversation_history[-10:]:  # Берем последние 10 сообщений
            if msg['role'] == 'user':
                conversation_text += f"{role_label_user}: {msg['content']}\n"
            else:
                conversation_text += f"{role_label_ai}: {msg['content']}\n"
        
        # Формируем полный промпт с системной инструкцией
        full_prompt = f"""{system_instruction}

Continue the following store dialogue:

{conversation_text}

Your response as {role_label_ai} (in English only):"""
        
        return self.generate_text(full_prompt)