import sqlite3
import json
from datetime import datetime
from config import DATABASE_FILE


class Database:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.init_database()
    
    def get_connection(self):
        """Получить соединение с базой данных"""
        return sqlite3.connect(self.db_file)
    
    def init_database(self):
        """Инициализировать таблицы базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для хранения диалогов (покупатель-продавец)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dialogues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                messages TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица для изучения слов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                topic TEXT,
                words TEXT,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица для результатов тестов по грамматике
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grammar_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                test_data TEXT,
                score INTEGER,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username=None, first_name=None):
        """Добавить пользователя в базу данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        
        conn.commit()
        conn.close()
    
    def save_dialogue(self, user_id, messages):
        """Сохранить диалог пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        messages_json = json.dumps(messages, ensure_ascii=False)
        cursor.execute('''
            INSERT INTO dialogues (user_id, messages)
            VALUES (?, ?)
        ''', (user_id, messages_json))
        
        conn.commit()
        conn.close()
    
    def save_vocabulary(self, user_id, topic, words):
        """Сохранить слова по теме для пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        words_json = json.dumps(words, ensure_ascii=False)
        cursor.execute('''
            INSERT INTO vocabulary (user_id, topic, words)
            VALUES (?, ?, ?)
        ''', (user_id, topic, words_json))
        
        conn.commit()
        conn.close()
    
    def get_user_vocabulary(self, user_id):
        """Получить все сохраненные слова пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT topic, words, learned_at
            FROM vocabulary
            WHERE user_id = ?
            ORDER BY learned_at DESC
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'topic': row[0],
                'words': json.loads(row[1]),
                'learned_at': row[2]
            }
            for row in results
        ]
    
    def save_test_result(self, user_id, test_data, score):
        """Сохранить результат теста"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        test_json = json.dumps(test_data, ensure_ascii=False)
        cursor.execute('''
            INSERT INTO grammar_tests (user_id, test_data, score)
            VALUES (?, ?, ?)
        ''', (user_id, test_json, score))
        
        conn.commit()
        conn.close()
    
    def get_user_test_history(self, user_id):
        """Получить историю тестов пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT score, completed_at
            FROM grammar_tests
            WHERE user_id = ?
            ORDER BY completed_at DESC
            LIMIT 10
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'score': row[0],
                'completed_at': row[1]
            }
            for row in results
        ]