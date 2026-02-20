import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from datetime import datetime
import time
import threading

# Токен твоего бота
TOKEN = "8118830152:AAFd-kjnFGYkPu4u41axst10Vo1gbNWKBjo"
ADMIN_ID ="1836497867"

bot = telebot.TeleBot(TOKEN)
DB_NAME = "reminders.db"

# --- ФУНКЦИЯ ДЛЯ ОТПРАВКИ УВЕДОМЛЕНИЙ АДМИНУ ---
def notify_admin(message_text):
    """Отправляет уведомление администратору"""
    try:
        bot.send_message(ADMIN_ID, message_text)
        print("Уведомление админу отправлено")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление админу: {e}")
        return False

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            remind_time TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)
    conn.commit()
    conn.close()
    print("База данных подключена!")
    notify_admin("Бот запущен и база данных подключена!")

def add_reminder(user_id, text, remind_time):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (user_id, text, remind_time) VALUES (?, ?, ?)",
        (user_id, text, remind_time)
    )
    reminder_id = cur.lastrowid
    conn.commit()
    conn.close()
    return reminder_id

def get_active_reminders():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, text, remind_time FROM reminders WHERE status = 'active'"
    )
    reminders = cur.fetchall()
    conn.close()
    return reminders

def mark_reminder_as_sent(reminder_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE reminders SET status = 'sent' WHERE id = ?",
        (reminder_id,)
    )
    conn.commit()
    conn.close()

def get_user_reminders(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, text, remind_time, status FROM reminders WHERE user_id = ? ORDER BY remind_time",
        (user_id,)
    )
    reminders = cur.fetchall()
    conn.close()
    return reminders

# --- ФУНКЦИЯ ПРОВЕРКИ НАПОМИНАНИЙ ---
def check_reminders():
    print("Поток проверки напоминаний запущен!")
    while True:
        try:
            reminders = get_active_reminders()
            
            for reminder_id, user_id, text, remind_time_str in reminders:
                remind_time = datetime.strptime(remind_time_str, "%Y-%m-%d %H:%M:%S")
                
                if datetime.now() >= remind_time:
                    try:
                        bot.send_message(
                            user_id,
                            f"НАПОМИНАНИЕ!\n\n{text}"
                        )
                        mark_reminder_as_sent(reminder_id)
                        print(f"Напоминание {reminder_id} отправлено пользователю {user_id}")
                        
                        # Уведомление админу об отправленном напоминании
                        notify_admin(f"Напоминание {reminder_id} отправлено пользователю {user_id}")
                        
                    except Exception as e:
                        print(f"Ошибка отправки напоминания {reminder_id}: {e}")
                        notify_admin(f"Ошибка отправки напоминания {reminder_id}: {e}")
            
            time.sleep(30)
            
        except Exception as e:
            print(f"Ошибка в потоке проверки: {e}")
            time.sleep(60)




# --- КОМАНДА /start (с уведомлением админу) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    user_id = user.id
    username = user.username or "нет username"
    first_name = user.first_name or "нет имени"
    
    # Отправляем уведомление админу
    admin_message = f"""
НОВЫЙ ПОЛЬЗОВАТЕЛЬ!

Имя: {first_name}
ID: {user_id}
Username: @{username}
Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}
    """
    notify_admin(admin_message)
    print(admin_message)
    
    welcome_text = f"""
Привет, {first_name}!

Я бот-напоминалка!

Команды:
/start - это сообщение
/help - помощь
/error - сообщить об ошибке
/menu - открыть меню
/my - мои напоминания

Напиши /menu чтобы начать
    """
    bot.reply_to(message, welcome_text)
    





# --- КОМАНДА /help ---
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
Помощь по командам:

/start - начальное приветствие
/help - это сообщение
/error - сообщить об ошибке
/menu - открыть меню с кнопками
/my - показать все мои напоминания

Как создать напоминание:
1. Нажми /menu
2. Выбери "Создать напоминание"
3. Введи текст
4. Введи время в формате: ДД.ММ.ГГГГ ЧЧ:ММ
    """
    bot.reply_to(message, help_text)





# --- КОМАНДА /my ---
@bot.message_handler(commands=['my'])
def show_my_reminders(message):
    user_id = message.from_user.username
    reminders = get_user_reminders(user_id)
    
    if not reminders:
        bot.send_message(
            message.chat.id,
            "У вас пока нет напоминаний.\nСоздайте через /menu"
        )
        return
    
    text = "ВАШИ НАПОМИНАНИЯ:\n\n"
    for rem_id, rem_text, rem_time, status in reminders:
        dt = datetime.strptime(rem_time, "%Y-%m-%d %H:%M:%S")
        time_str = dt.strftime("%d.%m.%Y %H:%M")
        
        if status == "active":
            status_text = "[Ожидает]"
        else:
            status_text = "[Отправлено]"
            
        text += f"{status_text} {time_str} - {rem_text}\n"
    
    bot.send_message(message.chat.id, text)





# --- КОМАНДА /menu с кнопками ---
@bot.message_handler(commands=['menu'])
def show_menu(message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    btn_create = InlineKeyboardButton("Создать напоминание", callback_data="create_reminder")
    btn_list = InlineKeyboardButton("Мои напоминания", callback_data="list_reminders")
    btn_help = InlineKeyboardButton("Помощь", callback_data="help_menu")
    
    keyboard.add(btn_create, btn_list, btn_help)
    
    bot.send_message(
        message.chat.id,
        "ГЛАВНОЕ МЕНЮ:\nВыберите действие:",
        reply_markup=keyboard
    )




# --- ОБРАБОТЧИК НАЖАТИЙ НА КНОПКИ ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "create_reminder":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            call.message.chat.id,
            "Напишите текст напоминания:"
        )
        bot.register_next_step_handler(msg, get_reminder_text)
        
    elif call.data == "list_reminders":
        bot.answer_callback_query(call.id)
        show_my_reminders(call.message)
        
    elif call.data == "help_menu":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "ПОМОЩЬ ПО МЕНЮ:\n\n"
            "Создать напоминание - создать новое напоминание\n"
            "Мои напоминания - посмотреть все напоминания\n\n"
            "После создания я пришлю уведомление в указанное время!"
        )


# --- ФУНКЦИИ СОЗДАНИЯ НАПОМИНАНИЯ ---
def get_reminder_text(message):
    """Получает текст напоминания"""
    text = message.text
    
    msg = bot.send_message(
        message.chat.id,
        "Теперь напишите время в формате:\n"
        "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
        "Например: 25.12.2024 15:30"
    )
    bot.register_next_step_handler(msg, get_reminder_time, text)

def get_reminder_time(message, reminder_text):
    """Получает время и сохраняет напоминание"""
    try:
        remind_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        
        if remind_time < datetime.now():
            bot.send_message(
                message.chat.id,
                "Ошибка! Нельзя создать напоминание на прошедшее время!\n"
                "Попробуйте снова через /menu"
            )
            return
        
        time_str = remind_time.strftime("%Y-%m-%d %H:%M:%S")
        reminder_id = add_reminder(
            message.from_user.id,
            reminder_text,
            time_str
        )
        
        bot.send_message(
            message.chat.id,
            f"НАПОМИНАНИЕ СОЗДАНО!\n\n"
            f"Текст: {reminder_text}\n"
            f"Время: {remind_time.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Я напомню вам в это время!"
        )
        
        show_menu(message)
        
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Ошибка! Неправильный формат времени!\n"
            "Используйте: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2024 15:30\n\n"
            "Попробуйте снова через /menu"
        )



# --- КОМАНДА /error ---
@bot.message_handler(commands=['error'])
def ask_for_error(message):
    msg = bot.send_message(
        message.chat.id,
        "Опишите ошибку, с которой вы столкнулись:"
    )
    bot.register_next_step_handler(msg, process_error)

def process_error(message):
    user = message.from_user
    username = user.username or "нет username"
    first_name = user.first_name or "нет имени"
    user_id = user.id
    error_text = message.text
    
    admin_message = f"""
НОВОЕ СООБЩЕНИЕ ОБ ОШИБКЕ

От пользователя:
Имя: {first_name}
ID: {user_id}
Username: @{username}

Текст ошибки:
{error_text}
    """
    
    try:
        bot.send_message(ADMIN_ID, admin_message)
        bot.send_message(
            message.chat.id,
            "Спасибо! Сообщение об ошибке отправлено разработчику."
        )
    except:
        bot.send_message(
            message.chat.id,
            "Ошибка при отправке. Попробуйте позже."
        )

# --- Обработчик всех остальных сообщений ---
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(
        message, 
        "Я понимаю только команды:\n/start\n/help\n/error\n/menu\n/my"
    )

# --- ЗАПУСК БОТА ---
if __name__ == "__main__":
    init_db()
    reminder_thread = threading.Thread(target=check_reminders, daemon=True)
    reminder_thread.start()
    print("Бот запущен...")
    time.sleep(5)
    bot.infinity_polling()
