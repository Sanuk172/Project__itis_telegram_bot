import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from config import TELEGRAM_BOT_TOKEN
from database import Database
from grammar_test import GrammarTest
from dialogue import Dialogue
from vocabulary import Vocabulary

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    WAITING_FOR_TEST_ANSWER,
    WAITING_FOR_VOCAB_TOPIC,
    WAITING_FOR_DIALOGUE_MESSAGE,
) = range(3)

# Глобальные объекты
db = Database()
grammar_tests = {}  # Храним тесты для каждого пользователя
dialogues = Dialogue()
vocabulary_service = Vocabulary()
dialogue_states = {}  # Храним состояние диалогов (ключ для ConversationHandler)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для изучения английского языка с помощью Gemini AI.

Доступные функции:
📝 /test - Создать тест по временам английского языка
💬 /dialogue - Начать диалог (покупатель-продавец)
📚 /vocabulary - Изучить новые слова по теме
📊 /history - Посмотреть историю тестов и изученных слов
ℹ️ /help - Помощь по командам

Выберите функцию:
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Тест по грамматике", callback_data="menu_test"),
            InlineKeyboardButton("💬 Диалог", callback_data="menu_dialogue")
        ],
        [
            InlineKeyboardButton("📚 Изучить слова", callback_data="menu_vocabulary"),
            InlineKeyboardButton("📊 История", callback_data="menu_history")
        ],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 *Помощь по командам:*

*/start* - Главное меню
*/test* - Создать тест по временам английского языка
  Выберите тип времен (Present, Past, Future или все)
  Ответьте на вопросы, выбрав вариант a, b, c или d
  
*/dialogue* - Начать диалог в роли продавца или покупателя
  Практикуйте английский в реальных ситуациях
  ИИ проверяет вашу грамматику после каждого сообщения
  Диалог автоматически завершается после 10 обменов
  
*/vocabulary* - Изучить новые слова по конкретной теме
  Укажите тему, и бот сгенерирует список слов с примерами
  
*/history* - Посмотреть историю ваших тестов и изученных слов

*/cancel* - Отменить текущее действие

Удачи в изучении английского! 🚀
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "menu_test":
        await query.edit_message_text(
            "📝 Выберите тип времен для теста:",
            reply_markup=get_tense_keyboard()
        )
    elif data == "menu_dialogue":
        await query.edit_message_text(
            "💬 Выберите вашу роль в диалоге:\n\n"
            "👨‍💼 Продавец - вы будете продавцом, ИИ - покупателем\n"
            "🛒 Покупатель - вы будете покупателем, ИИ - продавцом\n\n"
            "📝 ИИ будет проверять вашу грамматику\n"
            "⏱️ Диалог завершится после 10 обменов репликами",
            reply_markup=get_role_keyboard()
        )
    elif data == "menu_vocabulary":
        await query.message.reply_text(
            "📚 Введите тему для изучения слов (например: 'food', 'travel', 'technology'):"
        )
        dialogue_states[query.from_user.id] = WAITING_FOR_VOCAB_TOPIC
    elif data == "menu_history":
        await show_history(query.from_user.id, query, is_callback=True)
    elif data == "menu_help":
        help_text = """
📖 *Помощь по командам:*

*/start* - Главное меню
*/test* - Создать тест по временам английского языка
*/dialogue* - Начать диалог в роли продавца или покупателя
*/vocabulary* - Изучить новые слова по конкретной теме
*/history* - Посмотреть историю ваших тестов и изученных слов
*/cancel* - Отменить текущее действие

Удачи в изучении английского! 🚀
        """
        await query.edit_message_text(help_text, parse_mode='Markdown')
    elif data == "menu_back":
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=get_main_keyboard()
        )
    elif data.startswith("tense_"):
        tense = data.replace("tense_", "")
        await start_test_callback(query, context, tense)
    elif data.startswith("role_"):
        # Роль пользователя
        user_role = "seller" if "seller" in data else "buyer"
        await start_dialogue_callback(query, context, user_role)


def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Тест по грамматике", callback_data="menu_test"),
            InlineKeyboardButton("💬 Диалог", callback_data="menu_dialogue")
        ],
        [
            InlineKeyboardButton("📚 Изучить слова", callback_data="menu_vocabulary"),
            InlineKeyboardButton("📊 История", callback_data="menu_history")
        ],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tense_keyboard():
    """Клавиатура для выбора типа времен"""
    keyboard = [
        [
            InlineKeyboardButton("Все времена", callback_data="tense_all"),
            InlineKeyboardButton("Present", callback_data="tense_present")
        ],
        [
            InlineKeyboardButton("Past", callback_data="tense_past"),
            InlineKeyboardButton("Future", callback_data="tense_future")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_role_keyboard():
    """Клавиатура для выбора роли в диалоге"""
    keyboard = [
        [
            InlineKeyboardButton("👨‍💼 Я - Продавец", callback_data="role_seller"),
            InlineKeyboardButton("🛒 Я - Покупатель", callback_data="role_buyer")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_back")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_test_callback(query, context: ContextTypes.DEFAULT_TYPE, tense_type):
    """Начать тест по грамматике через callback"""
    user_id = query.from_user.id
    
    await query.message.reply_text("⏳ Создаю тест... Это может занять несколько секунд.")
    
    # Создаем тест
    test = GrammarTest()
    success, message = test.create_test(tense_type)
    
    if not success:
        await query.message.reply_text(f"❌ Ошибка: {message}")
        return
    
    grammar_tests[user_id] = test
    dialogue_states[user_id] = WAITING_FOR_TEST_ANSWER
    
    # Получаем первый вопрос
    question_data = test.get_current_question()
    if question_data:
        question_text = test.format_question_text(question_data)
        await query.message.reply_text(question_text)
    else:
        await query.message.reply_text("❌ Не удалось создать тест")


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /test"""
    await update.message.reply_text(
        "📝 Выберите тип времен для теста:",
        reply_markup=get_tense_keyboard()
    )


async def handle_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать ответ на вопрос теста"""
    user_id = update.effective_user.id
    user_answer = update.message.text.strip().lower()
    
    if user_id not in grammar_tests:
        await update.message.reply_text("Тест не найден. Начните новый тест с /test")
        return ConversationHandler.END
    
    test = grammar_tests[user_id]
    
    # Проверяем формат ответа
    if user_answer not in ['a', 'b', 'c', 'd']:
        await update.message.reply_text("Пожалуйста, выберите вариант ответа: a, b, c или d")
        return WAITING_FOR_TEST_ANSWER
    
    # Отправляем ответ
    success, result = test.submit_answer(user_answer)
    
    if not success:
        await update.message.reply_text(f"Ошибка: {result}")
        dialogue_states.pop(user_id, None)
        if user_id in grammar_tests:
            del grammar_tests[user_id]
        return ConversationHandler.END
    
    # Формируем ответ с результатом
    if isinstance(result, dict):
        correctness = "✅ Правильно!" if result['is_correct'] else f"❌ Неправильно. Правильный ответ: {result['correct_answer']}"
        response_text = f"{correctness}\n\n"
        response_text += f"💡 Объяснение: {result['explanation']}\n\n"
        
        # Получаем следующий вопрос
        next_question = test.get_current_question()
        if next_question:
            response_text += test.format_question_text(next_question)
            await update.message.reply_text(response_text)
            return WAITING_FOR_TEST_ANSWER
        else:
            # Тест завершен
            test_results = test.get_results()
            response_text += f"\n🎉 Тест завершен!\n\n"
            response_text += f"Правильных ответов: {test_results['correct_answers']}/{test_results['total_questions']}\n"
            response_text += f"Оценка: {test_results['score']}%"
            
            # Сохраняем результат
            db.save_test_result(user_id, test_results, test_results['score'])
            
            await update.message.reply_text(response_text)
            del grammar_tests[user_id]
            dialogue_states.pop(user_id, None)
            return ConversationHandler.END
    else:
        await update.message.reply_text("Ошибка при обработке ответа")
        dialogue_states.pop(user_id, None)
        if user_id in grammar_tests:
            del grammar_tests[user_id]
        return ConversationHandler.END


async def start_dialogue_callback(query, context: ContextTypes.DEFAULT_TYPE, user_role):
    """Начать диалог через callback"""
    user_id = query.from_user.id
    
    # ИИ играет противоположную роль
    ai_role = "buyer" if user_role == "seller" else "seller"
    
    initial_message = dialogues.start_dialogue(user_id, user_role, ai_role)
    
    role_text = "продавец" if user_role == "seller" else "покупатель"
    ai_role_text = "покупатель" if ai_role == "buyer" else "продавец"
    
    await query.message.reply_text(
        f"💬 *Диалог начат!*\n\n"
        f"👤 Вы: {role_text}\n"
        f"🤖 ИИ: {ai_role_text}\n"
        f"📊 Обменов: 0/{dialogues.MAX_EXCHANGES}\n\n"
        f"*ИИ ({ai_role_text}):*\n{initial_message}\n\n"
        f"✏️ Напишите ваш ответ на английском языке\n"
        f"📝 Ваша грамматика будет проверяться\n"
        f"❌ /cancel - завершить досрочно",
        parse_mode='Markdown'
    )
    dialogue_states[user_id] = WAITING_FOR_DIALOGUE_MESSAGE


async def dialogue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /dialogue"""
    await update.message.reply_text(
        "💬 Выберите вашу роль в диалоге:\n\n"
        "👨‍💼 Продавец - вы будете продавцом, ИИ - покупателем\n"
        "🛒 Покупатель - вы будете покупателем, ИИ - продавцом\n\n"
        "📝 ИИ будет проверять вашу грамматику\n"
        "⏱️ Диалог завершится после 10 обменов репликами",
        reply_markup=get_role_keyboard()
    )


def format_grammar_feedback(grammar_check):
    """Форматировать обратную связь по грамматике"""
    if grammar_check['errors_count'] == 0:
        return "✅ *Грамматика:* Отлично! Ошибок нет."
    
    text = f"📝 *Проверка грамматики:* Найдено ошибок: {grammar_check['errors_count']}\n"
    
    if grammar_check['corrected_text'] != grammar_check.get('original', ''):
        text += f"✏️ *Исправленный вариант:* _{grammar_check['corrected_text']}_\n"
    
    if grammar_check['mistakes']:
        text += "\n*Ошибки:*\n"
        for mistake in grammar_check['mistakes'][:5]:  # Показываем максимум 5 ошибок
            text += f"{mistake}\n"
    
    return text


def format_dialogue_statistics(stats):
    """Форматировать статистику диалога"""
    if not stats:
        return ""
    
    text = "\n\n📊 *СТАТИСТИКА ДИАЛОГА*\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💬 Всего обменов: {stats['total_exchanges']}\n"
    text += f"❌ Всего ошибок: {stats['total_errors']}\n"
    
    # Оценка на основе общего количества ошибок
    if stats['total_errors'] == 0:
        grade = "🌟 Превосходно!"
    elif stats['total_errors'] <= 3:
        grade = "👍 Хорошо!"
    elif stats['total_errors'] <= 7:
        grade = "📚 Неплохо, но есть над чем работать"
    else:
        grade = "💪 Продолжайте практиковаться!"
    
    text += f"\n*Оценка:* {grade}\n"
    
    # Показываем последние ошибки
    if stats['all_mistakes']:
        text += "\n*Последние ошибки для повторения:*\n"
        for mistake in stats['all_mistakes'][-5:]:
            text += f"• {mistake}\n"
    
    return text


async def handle_dialogue_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать сообщение в диалоге"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if not dialogues.is_active(user_id):
        await update.message.reply_text("Диалог не активен. Начните новый диалог с /dialogue")
        dialogue_states.pop(user_id, None)
        return ConversationHandler.END
    
    # Получаем роль ИИ для отображения
    ai_role = dialogues.get_ai_role(user_id)
    ai_role_text = "Покупатель" if ai_role == "buyer" else "Продавец"
    
    # Отправляем сообщение и получаем результат
    result = dialogues.send_message(user_id, user_message)
    
    # Формируем ответ
    response_text = ""
    
    # 1. Проверка грамматики
    grammar_feedback = format_grammar_feedback(result['grammar_check'])
    response_text += grammar_feedback + "\n\n"
    
    # 2. Прогресс диалога
    response_text += f"📊 Обмен {result['current_exchange']}/{result['max_exchanges']}\n\n"
    
    # 3. Ответ ИИ
    response_text += f"🤖 *{ai_role_text}:*\n{result['response']}"
    
    await update.message.reply_text(response_text, parse_mode='Markdown')
    
    # Проверяем, завершён ли диалог
    if result['is_finished']:
        stats_text = format_dialogue_statistics(result['stats'])
        
        await update.message.reply_text(
            f"🎉 *Диалог завершён!*{stats_text}\n\n"
            f"Используйте /dialogue для нового диалога или /start для главного меню.",
            parse_mode='Markdown'
        )
        
        # Завершаем диалог
        dialogues.end_dialogue(user_id)
        dialogue_states.pop(user_id, None)
        return ConversationHandler.END
    
    return WAITING_FOR_DIALOGUE_MESSAGE


async def vocabulary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /vocabulary"""
    await update.message.reply_text(
        "📚 Введите тему для изучения слов (например: 'food', 'travel', 'technology'):"
    )
    dialogue_states[update.effective_user.id] = WAITING_FOR_VOCAB_TOPIC
    return WAITING_FOR_VOCAB_TOPIC


async def handle_vocabulary_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать тему для изучения слов"""
    user_id = update.effective_user.id
    topic = update.message.text.strip()
    
    if not topic:
        await update.message.reply_text("Пожалуйста, укажите тему для изучения слов.")
        return WAITING_FOR_VOCAB_TOPIC
    
    await update.message.reply_text("⏳ Генерирую слова... Это может занять несколько секунд.")
    
    # Генерируем слова
    success, vocabulary_data = vocabulary_service.generate_words(topic, 10)
    
    if not success:
        await update.message.reply_text(f"❌ Ошибка: {vocabulary_data}")
        dialogue_states.pop(user_id, None)
        return ConversationHandler.END
    
    # Сохраняем слова
    vocabulary_service.save_words(user_id, vocabulary_data)
    
    # Форматируем и отправляем
    words_text = vocabulary_service.format_words_compact(vocabulary_data)
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(words_text) > 4096:
        words_text_parts = [words_text[i:i+4096] for i in range(0, len(words_text), 4096)]
        for part in words_text_parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(words_text, parse_mode='Markdown')
    
    await update.message.reply_text(
        "✅ Слова сохранены! Используйте /history чтобы посмотреть все изученные слова."
    )
    
    dialogue_states.pop(user_id, None)
    return ConversationHandler.END


async def show_history(user_id, message_or_query, is_callback=False):
    """Показать историю пользователя"""
    # Получаем историю тестов
    test_history = db.get_user_test_history(user_id)
    
    # Получаем историю слов
    vocab_history = vocabulary_service.get_user_vocabulary_history(user_id)
    
    text = "📊 *Ваша история:*\n\n"
    
    if test_history:
        text += "📝 *Последние тесты:*\n"
        for test in test_history[:5]:
            text += f"• Оценка: {test['score']}% ({test['completed_at']})\n"
        text += "\n"
    else:
        text += "📝 Тесты еще не пройдены\n\n"
    
    if vocab_history:
        text += "📚 *Изученные темы:*\n"
        for vocab in vocab_history[:5]:
            text += f"• {vocab['topic']} ({vocab['learned_at']})\n"
    else:
        text += "📚 Темы еще не изучены"
    
    if is_callback:
        await message_or_query.edit_message_text(text, parse_mode='Markdown')
    else:
        await message_or_query.reply_text(text, parse_mode='Markdown')


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /history"""
    user_id = update.effective_user.id
    await show_history(user_id, update.message, is_callback=False)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить текущее действие"""
    user_id = update.effective_user.id
    
    # Очищаем состояния
    if user_id in grammar_tests:
        del grammar_tests[user_id]
    
    # Если был активный диалог, показываем статистику
    if dialogues.is_active(user_id):
        stats = dialogues.end_dialogue(user_id)
        if stats and stats['total_exchanges'] > 0:
            stats_text = format_dialogue_statistics(stats)
            await update.message.reply_text(
                f"❌ *Диалог завершён досрочно*{stats_text}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Действие отменено.")
    else:
        await update.message.reply_text("❌ Действие отменено.")
    
    dialogue_states.pop(user_id, None)
    
    await update.message.reply_text("Используйте /start для начала.")
    return ConversationHandler.END


def main():
    """Главная функция для запуска бота"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == '':
        logger.error("TELEGRAM_BOT_TOKEN не установлен! Создайте файл .env")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик команды /help
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик кнопок (должен быть перед ConversationHandlers)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # ConversationHandler для тестов (команда /test)
    test_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("test", test_command)],
        states={
            WAITING_FOR_TEST_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_test_answer)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(test_conv_handler)
    
    # ConversationHandler для диалогов (команда /dialogue)
    dialogue_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("dialogue", dialogue_command)],
        states={
            WAITING_FOR_DIALOGUE_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dialogue_message)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(dialogue_conv_handler)
    
    # ConversationHandler для изучения слов (ПЕРЕД универсальным обработчиком!)
    vocab_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("vocabulary", vocabulary_command)],
        states={
            WAITING_FOR_VOCAB_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vocabulary_topic)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(vocab_conv_handler)
    
    # Универсальный обработчик сообщений для состояний через кнопки (добавляется ПОСЛЕДНИМ)
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Проверяем, активен ли тест (через кнопку)
        if user_id in grammar_tests:
            await handle_test_answer(update, context)
            return
        
        # Проверяем, активен ли диалог (через кнопку)
        if dialogues.is_active(user_id) and dialogue_states.get(user_id) == WAITING_FOR_DIALOGUE_MESSAGE:
            await handle_dialogue_message(update, context)
            return
        
        # Проверяем, ожидаем ли тему для словаря (через кнопку)
        if dialogue_states.get(user_id) == WAITING_FOR_VOCAB_TOPIC:
            await handle_vocabulary_topic(update, context)
            return
    
    # Обработчик команды /history
    application.add_handler(CommandHandler("history", history_command))
    
    # Обработчик команды /cancel
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Универсальный обработчик (должен быть ПОСЛЕ всех команд и ConversationHandler)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
