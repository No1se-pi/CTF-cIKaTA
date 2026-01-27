import telebot
import sqlite3
from datetime import datetime

# Конфигурация бота
TOKEN = "7895480716:AAFJXwNGvpCjhTWZ9TdwnbycUnAKl2wIees"
TEAM_NAME = "CTFTeam"
ADMIN_PASSWORD = "qwerty123"
admins = []
start_message = f"Это бот принадлежит команде {TEAM_NAME} и пока не взломан"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('ctf_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Создаем таблицу пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Проверяем и добавляем тестовых пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            (1, 'admin', 'SuperSecret123!', 1),
            (2, 'alice', 'AlicePassword2024', 0),
            (3, 'bob', 'BobIsTheBest', 0),
            (4, 'charlie', 'Charlie123', 0),
        ]
        
        for user in users:
            sql = f"INSERT INTO users (id, username, password, is_admin) VALUES ({user[0]}, '{user[1]}', '{user[2]}', {user[3]})"
            try:
                cursor.execute(sql)
            except:
                pass
    
    conn.commit()
    conn.close()

# Инициализируем базу данных
init_db()

bot = telebot.TeleBot(TOKEN)

def is_admin(user_id):
    """Проверяет, является ли пользователь админом"""
    return user_id in admins

def check_login(username, password):
    """Аутентификация пользователя"""
    conn = sqlite3.connect('ctf_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    query = f"SELECT id, username, is_admin FROM users WHERE username='{username}' AND password='{password}'"
    
    try:
        cursor.execute(query)
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        conn.close()
        return None

def search_user(search_term):
    """Поиск пользователей в базе данных"""
    conn = sqlite3.connect('ctf_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    query = f"SELECT username, password FROM users WHERE username LIKE '%{search_term}%' OR password LIKE '%{search_term}%'"
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        conn.close()
        return []

@bot.message_handler(commands=['start', 'flag'])
def send_welcome(message):
    """Обработчик команд /start и /flag"""
    bot.reply_to(message, start_message)

@bot.message_handler(commands=['help'])
def show_help(message):
    """Показывает список доступных команд"""
    help_text = """📋 Доступные команды:

Для всех пользователей:
/start, /flag - Стартовое сообщение
/help - Эта справка
/login [логин] [пароль] - Войти в систему
/search [текст] - Поиск пользователей
/addadmin [пароль] - Стать админом (нужен пароль)

Только для админов:
/database - Показать всю базу данных
/adminall - Список всех админов
/changestart [текст] - Изменить стартовое сообщение
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['login'])
def login_command(message):
    """Обработчик команды /login"""
    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Использование: /login [логин] [пароль]")
            return
        
        username = parts[1]
        password = parts[2]
        
        result = check_login(username, password)
        
        if result:
            user_id, username, is_admin_flag = result
            if is_admin_flag:
                admins.append(message.from_user.id)
                bot.reply_to(message, f"✅ Вход успешен! Вы администратор, {username}")
            else:
                bot.reply_to(message, f"✅ Вход успешен! Добро пожаловать, {username}")
        else:
            bot.reply_to(message, "❌ Неверный логин или пароль")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['search'])
def search_command(message):
    """Обработчик команды /search"""
    try:
        if len(message.text.split()) < 2:
            bot.reply_to(message, "❌ Использование: /search [текст]")
            return
        
        search_term = ' '.join(message.text.split(' ')[1:])
        results = search_user(search_term)
        
        if results:
            response = "🔍 Результаты поиска:\n"
            for username, password in results[:10]:
                response += f"│ {username:<15}│ Такой пользователь есть!\n"
            
        else:
            response = "🔍 Ничего не найдено"
        
        bot.reply_to(message, response)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка поиска: {str(e)}")

@bot.message_handler(commands=['addadmin'])
def add_admin_command(message):
    """Обработчик команды /addadmin"""
    try:
        if len(message.text.split()) < 2:
            bot.reply_to(message, "❌ Использование: /addadmin [пароль]")
            return
        
        password = message.text.split(' ', 1)[1]
        
        if password == ADMIN_PASSWORD:
            if message.from_user.id not in admins:
                admins.append(message.from_user.id)
                bot.reply_to(message, f"✅ Вы стали админом! Ваш ID: {message.from_user.id}")
            else:
                bot.reply_to(message, "⚠️ Вы уже админ!")
        else:
            bot.reply_to(message, "❌ Неверный пароль админа!")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['database'])
def show_database(message):
    """Обработчик команды /database"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только для админов!")
        return
    
    try:
        conn = sqlite3.connect('ctf_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, password, is_admin FROM users")
        users = cursor.fetchall()
        
        response = "👥 База данных пользователей:\n"
        response += "┌─────────────────┬─────────────────────────┬─────────┐\n"
        response += "│     Логин       │       Пароль            │  Admin  │\n"
        response += "├─────────────────┼─────────────────────────┼─────────┤\n"
        
        for username, password, is_admin_flag in users:
            admin_status = "✅" if is_admin_flag else "❌"
            response += f"│ {username:<15} │ {password:<23} │ {admin_status:<7} │\n"
        
        response += "└─────────────────┴─────────────────────────┴─────────┘\n"
        response += f"📊 Всего пользователей: {len(users)}"
        
        conn.close()
        bot.reply_to(message, response)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка БД: {str(e)}")

@bot.message_handler(commands=['adminall'])
def show_admins(message):
    """Обработчик команды /adminall"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только для админов!")
        return
    
    response = "👑 Список админов (ID Telegram):\n"
    for admin_id in admins:
        response += f"• {admin_id}\n"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['changestart'])
def change_start(message):
    """Обработчик команды /changestart"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только для админов!")
        return
    
    try:
        global start_message
        new_message = message.text.split(' ', 1)[1].strip()
        start_message = new_message
        bot.reply_to(message, f"✅ Стартовое сообщение изменено!")
    except IndexError:
        bot.reply_to(message, "❌ Использование: /changestart [текст]")


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обработчик всех остальных сообщений"""
    bot.reply_to(message, "🤖 Неизвестная команда. Напишите /help для списка команд")

if __name__ == "__main__":
    print(f"🤖 CTF Bot запущен с токеном: {TOKEN[:10]}...")
    print(f"👥 Команда: {TEAM_NAME}")
    print(f"🔑 Пароль админа: {ADMIN_PASSWORD}")
    print("⏳ Ожидание сообщений...\n")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")