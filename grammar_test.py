import re
from gemini_service import GeminiService


class GrammarTest:
    def __init__(self):
        self.gemini = GeminiService()
        self.current_test = None
        self.current_question_index = 0
        self.user_answers = []
    
    def parse_test_response(self, response):
        """Парсить текстовый ответ от Gemini и извлечь вопросы"""
        questions = []
        
        # Разбиваем по паттерну "ВОПРОС X:"
        question_blocks = re.split(r'ВОПРОС\s*\d+\s*:', response, flags=re.IGNORECASE)
        
        for block in question_blocks[1:]:  # Пропускаем первый пустой элемент
            if not block.strip():
                continue
            
            try:
                question_data = self.parse_question_block(block)
                if question_data:
                    questions.append(question_data)
            except Exception:
                continue
        
        return questions
    
    def parse_question_block(self, block):
        """Парсить отдельный блок вопроса"""
        lines = block.strip().split('\n')
        
        question_text = ""
        options = {}
        correct_answer = ""
        explanation = ""
        
        current_section = "question"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Проверяем варианты ответов
            option_match = re.match(r'^([a-d])\s*[\)\.]\s*(.+)', line, re.IGNORECASE)
            if option_match:
                options[option_match.group(1).lower()] = option_match.group(2).strip()
                continue
            
            # Проверяем правильный ответ
            answer_match = re.match(r'^ОТВЕТ\s*:\s*([a-d])', line, re.IGNORECASE)
            if answer_match:
                correct_answer = answer_match.group(1).lower()
                current_section = "answer"
                continue
            
            # Проверяем объяснение
            explanation_match = re.match(r'^ОБЪЯСНЕНИЕ\s*:\s*(.+)', line, re.IGNORECASE)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
                current_section = "explanation"
                continue
            
            # Добавляем к текущей секции
            if current_section == "question" and not options:
                question_text += " " + line if question_text else line
            elif current_section == "explanation":
                explanation += " " + line
        
        # Проверяем, что у нас есть все необходимые данные
        if question_text and len(options) >= 4 and correct_answer:
            return {
                "question": question_text.strip(),
                "options": options,
                "correct_answer": correct_answer,
                "explanation": explanation.strip() if explanation else "Нет объяснения"
            }
        
        return None
    
    def create_test(self, tense_type="all"):
        """Создать новый тест"""
        response = self.gemini.create_grammar_test(tense_type)
        
        # Проверяем на ошибку API
        if response.startswith("GEMINI_ERROR:"):
            return False, response.replace("GEMINI_ERROR: ", "")
        
        # Парсим текстовый ответ
        questions = self.parse_test_response(response)
        
        if questions and len(questions) >= 3:  # Минимум 3 вопроса для теста
            self.current_test = {
                "questions": questions,
                "tense_type": tense_type
            }
            self.current_question_index = 0
            self.user_answers = []
            return True, f"Тест создан успешно! ({len(questions)} вопросов)"
        else:
            # Попробуем ещё раз с упрощенным парсингом
            questions = self.fallback_parse(response)
            if questions and len(questions) >= 3:
                self.current_test = {
                    "questions": questions,
                    "tense_type": tense_type
                }
                self.current_question_index = 0
                self.user_answers = []
                return True, f"Тест создан успешно! ({len(questions)} вопросов)"
            
            return False, f"Не удалось создать тест. Попробуйте ещё раз. Ответ: {response[:300]}..."
    
    def fallback_parse(self, response):
        """Запасной метод парсинга - более гибкий"""
        questions = []
        
        # Ищем любые паттерны вопросов с вариантами
        # Паттерн: текст с вариантами a), b), c), d)
        pattern = r'(.+?)\n\s*a\s*[\)\.]\s*(.+?)\n\s*b\s*[\)\.]\s*(.+?)\n\s*c\s*[\)\.]\s*(.+?)\n\s*d\s*[\)\.]\s*(.+?)(?:\n|$)'
        
        matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
        
        for i, match in enumerate(matches):
            if len(match) >= 5:
                question_text = match[0].strip()
                # Убираем номер вопроса из текста
                question_text = re.sub(r'^\d+[\.\)]\s*', '', question_text)
                question_text = re.sub(r'^ВОПРОС\s*\d*\s*:?\s*', '', question_text, flags=re.IGNORECASE)
                
                options = {
                    'a': match[1].strip(),
                    'b': match[2].strip(),
                    'c': match[3].strip(),
                    'd': match[4].strip()
                }
                
                # Ищем ответ после вариантов
                answer_pattern = rf'{re.escape(match[4])}.*?(?:ОТВЕТ|Answer|Correct)\s*:?\s*([a-d])'
                answer_match = re.search(answer_pattern, response, re.IGNORECASE | re.DOTALL)
                correct_answer = answer_match.group(1).lower() if answer_match else 'a'
                
                # Ищем объяснение
                explanation = "Нет объяснения"
                expl_pattern = rf'{re.escape(match[4])}.*?(?:ОБЪЯСНЕНИЕ|Explanation)\s*:?\s*(.+?)(?:ВОПРОС|$)'
                expl_match = re.search(expl_pattern, response, re.IGNORECASE | re.DOTALL)
                if expl_match:
                    explanation = expl_match.group(1).strip()[:200]
                
                questions.append({
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": explanation
                })
        
        return questions
    
    def get_current_question(self):
        """Получить текущий вопрос"""
        if not self.current_test or not self.current_test.get('questions'):
            return None
        
        if self.current_question_index >= len(self.current_test['questions']):
            return None
        
        question = self.current_test['questions'][self.current_question_index]
        return {
            'number': self.current_question_index + 1,
            'total': len(self.current_test['questions']),
            'question': question['question'],
            'options': question['options'],
            'correct_answer': question.get('correct_answer'),
            'explanation': question.get('explanation', '')
        }
    
    def submit_answer(self, answer):
        """Отправить ответ на текущий вопрос"""
        if not self.current_test:
            return False, "Тест не начат"
        
        current_q = self.get_current_question()
        if not current_q:
            return False, "Вопрос не найден"
        
        answer_lower = answer.lower().strip()
        
        # Сохраняем ответ пользователя
        self.user_answers.append({
            'question_index': self.current_question_index,
            'user_answer': answer_lower,
            'correct_answer': current_q['correct_answer'],
            'is_correct': answer_lower == current_q['correct_answer'].lower()
        })
        
        is_correct = answer_lower == current_q['correct_answer'].lower()
        self.current_question_index += 1
        
        return True, {
            'is_correct': is_correct,
            'correct_answer': current_q['correct_answer'],
            'explanation': current_q['explanation']
        }
    
    def get_results(self):
        """Получить результаты теста"""
        if not self.current_test:
            return None
        
        total = len(self.current_test['questions'])
        correct = sum(1 for ans in self.user_answers if ans['is_correct'])
        score = int((correct / total) * 100) if total > 0 else 0
        
        results = {
            'total_questions': total,
            'correct_answers': correct,
            'score': score,
            'answers': self.user_answers,
            'tense_type': self.current_test.get('tense_type', 'all')
        }
        
        return results
    
    def format_question_text(self, question_data):
        """Форматировать вопрос для отображения"""
        if not question_data:
            return "Тест завершен или не начат"
        
        text = f"Вопрос {question_data['number']}/{question_data['total']}\n\n"
        text += f"{question_data['question']}\n\n"
        
        for key, value in question_data['options'].items():
            text += f"{key}) {value}\n"
        
        text += "\nВыберите вариант ответа (a, b, c или d):"
        
        return text

