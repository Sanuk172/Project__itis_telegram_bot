from gemini_service import GeminiService
from database import Database


class Dialogue:
    # Максимальное количество обменов репликами (пользователь + ИИ = 1 обмен)
    MAX_EXCHANGES = 10
    
    def __init__(self):
        self.gemini = GeminiService()
        self.db = Database()
        self.conversations = {}  # Храним истории диалогов для каждого пользователя
    
    def start_dialogue(self, user_id, user_role="buyer", ai_role="seller"):
        """Начать новый диалог
        
        user_role: роль пользователя (buyer или seller)
        ai_role: роль ИИ (противоположная роли пользователя)
        """
        self.conversations[user_id] = {
            'user_role': user_role,
            'ai_role': ai_role,
            'messages': [],
            'exchange_count': 0,  # Счётчик обменов репликами
            'total_errors': 0,    # Общее количество ошибок
            'errors_history': []  # История всех ошибок
        }
        
        # ИИ начинает диалог в своей роли
        if ai_role == "seller":
            initial_message = "Hello! Welcome to our store. How can I help you today?"
        else:
            initial_message = "Hello! I'm looking for some products. What do you have available?"
        
        self.conversations[user_id]['messages'].append({
            'role': 'assistant',
            'content': initial_message
        })
        
        return initial_message
    
    def send_message(self, user_id, user_message):
        """Отправить сообщение в диалог"""

        if user_id not in self.conversations:
            # Если диалог не начат, начинаем его с дефолтными ролями
            self.start_dialogue(user_id)
        
        conversation = self.conversations[user_id]
        ai_role = conversation['ai_role']
        
        # Проверяем грамматику сообщения пользователя
        grammar_result = self.gemini.check_grammar(user_message)
        
        # Обновляем статистику ошибок
        if grammar_result['errors_count'] > 0:
            conversation['total_errors'] += grammar_result['errors_count']
            conversation['errors_history'].extend(grammar_result['mistakes'])
        
        # Добавляем сообщение пользователя
        conversation['messages'].append({
            'role': 'user',
            'content': user_message
        })
        
        # Увеличиваем счётчик обменов
        conversation['exchange_count'] += 1
        
        # Проверяем, достигнут ли лимит
        is_finished = conversation['exchange_count'] >= self.MAX_EXCHANGES
        
        # Получаем ответ от ИИ (ИИ играет свою роль ai_role)
        response = self.gemini.continue_dialogue(
            conversation['messages'],
            user_message,
            ai_role
        )
        
        # Проверяем на ошибку API
        if response.startswith("GEMINI_ERROR:"):
            response = "Sorry, I couldn't process that. Could you please repeat?"
        
        # Добавляем ответ ИИ
        conversation['messages'].append({
            'role': 'assistant',
            'content': response
        })
        
        result = {
            'response': response,
            'grammar_check': grammar_result,
            'is_finished': is_finished,
            'current_exchange': conversation['exchange_count'],
            'max_exchanges': self.MAX_EXCHANGES,
            'stats': None
        }
        
        # Если диалог завершён, добавляем статистику
        if is_finished:
            result['stats'] = self.get_statistics(user_id)
        
        return result
    
    def get_statistics(self, user_id):
        """Получить статистику диалога"""
        if user_id not in self.conversations:
            return None
        
        conversation = self.conversations[user_id]
        
        return {
            'total_exchanges': conversation['exchange_count'],
            'total_errors': conversation['total_errors'],
            'errors_per_message': round(conversation['total_errors'] / max(conversation['exchange_count'], 1), 1),
            'all_mistakes': conversation['errors_history'][-10:]  # Последние 10 ошибок
        }
    
    def end_dialogue(self, user_id):
        """Завершить диалог и сохранить в БД"""
        if user_id in self.conversations:
            stats = self.get_statistics(user_id)
            messages = self.conversations[user_id]['messages']
            self.db.save_dialogue(user_id, messages)
            del self.conversations[user_id]
            return stats
        return None
    
    def get_user_role(self, user_id):
        """Получить роль пользователя в диалоге"""
        if user_id in self.conversations:
            return self.conversations[user_id].get('user_role', 'buyer')
        return None
    
    def get_ai_role(self, user_id):
        """Получить роль ИИ в диалоге"""
        if user_id in self.conversations:
            return self.conversations[user_id].get('ai_role', 'seller')
        return None
    
    def is_active(self, user_id):
        """Проверить, активен ли диалог"""
        return user_id in self.conversations
    
    def get_exchange_count(self, user_id):
        """Получить текущее количество обменов"""
        if user_id in self.conversations:
            return self.conversations[user_id].get('exchange_count', 0)
        return 0