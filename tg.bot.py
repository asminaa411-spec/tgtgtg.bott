import telebot
from telebot import types
import sqlite3
from datetime import date

TOKEN = "8658724899:AAH2cNrXOMARNn93EfohPpA4VbBAw00sM0A"

bot = telebot.TeleBot(TOKEN)

# работа с базой данных

def get_db():
    """подключение к базе"""
    conn = sqlite3.connect("wellness.db")
    return conn

def init_db():
    """создаём таблицы при первом запуске"""
    conn = get_db()
    cursor = conn.cursor()
    
    # таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT
        )
    """)
    
    # таблица записей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day DATE,
            mood INTEGER,
            work_hours REAL,
            sleep_hours REAL,
            comment TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("База готова!")

def add_user(telegram_id, name):
    """добавить пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)", 
                   (telegram_id, name))
    conn.commit()
    conn.close()

def get_user_id(telegram_id):
    """получить id пользователя из базы"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_record(user_id, mood, work, sleep, comment):
    """сохранить запись за день"""
    conn = get_db()
    cursor = conn.cursor()
    today = date.today()
    cursor.execute("""
        INSERT INTO records (user_id, day, mood, work_hours, sleep_hours, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, today, mood, work, sleep, comment))
    conn.commit()
    conn.close()

def get_all_records(user_id):
    """получить все записи пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT day, mood, work_hours, sleep_hours, comment FROM records WHERE user_id = ? ORDER BY day DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_records(user_id):
    """удалить все записи пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# КОМАНДЫ

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id, message.from_user.first_name)
    text = "Привет! Я бот для отслеживания настроения и продуктивности.\n\n"
    text += "Команды:\n"
    text += "/add - записать данные за сегодня\n"
    text += "/stats - статистика\n"
    text += "/insights - инсайты\n"
    text += "/history - история\n"
    text += "/clear - удалить данные\n"
    text += "/help - помощь"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = "Заполняй каждый день:\n"
    text += "1. Настроение (1-5)\n"
    text += "2. Часы работы/учёбы\n"
    text += "3. Часы сна\n\n"
    text += "Через неделю бот покажет закономерности!"
    bot.send_message(message.chat.id, text)

# ВВОД ДАННЫХ

# временное хранение 
user_temp = {}

@bot.message_handler(commands=['add'])
def add_data(message):
    user_temp[message.from_user.id] = {}
    
    # кнопки настроения
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("1 😞", callback_data="m1"),
        types.InlineKeyboardButton("2 😐", callback_data="m2"),
        types.InlineKeyboardButton("3 🙂", callback_data="m3"),
        types.InlineKeyboardButton("4 😊", callback_data="m4"),
        types.InlineKeyboardButton("5 🤩", callback_data="m5"),
    )
    
    bot.send_message(message.chat.id, "Оцени настроение от 1 до 5:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("m"))
def select_mood(call):
    mood = int(call.data[1])
    uid = call.from_user.id
    user_temp[uid]['mood'] = mood
    
    # кнопки часов работы
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("1 ч", callback_data="w1"),
        types.InlineKeyboardButton("2 ч", callback_data="w2"),
        types.InlineKeyboardButton("4 ч", callback_data="w4"),
        types.InlineKeyboardButton("6 ч", callback_data="w6"),
        types.InlineKeyboardButton("Другое", callback_data="w_other"),
    )
    
    bot.edit_message_text(f"Настроение: {mood}/5 \n\nСколько часов работал?", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("w"))
def select_work(call):
    uid = call.from_user.id
    val = call.data[1:]
    
    if val == "other":
        bot.edit_message_text("Напиши число часов (например 3.5):", call.message.chat.id, call.message.message_id)
        user_temp[uid]['waiting'] = 'work'
        return
    
    work = float(val)
    user_temp[uid]['work'] = work
    
    # кнопки сна
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("6 ч", callback_data="s6"),
        types.InlineKeyboardButton("7 ч", callback_data="s7"),
        types.InlineKeyboardButton("8 ч", callback_data="s8"),
        types.InlineKeyboardButton("9 ч", callback_data="s9"),
        types.InlineKeyboardButton("Другое", callback_data="s_other"),
    )
    
    bot.edit_message_text(f"Работа: {work} ч \n\nСколько спал?", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("s"))
def select_sleep(call):
    uid = call.from_user.id
    val = call.data[1:]
    
    if val == "other":
        bot.edit_message_text("Напиши число часов сна:", call.message.chat.id, call.message.message_id)
        user_temp[uid]['waiting'] = 'sleep'
        return
    
    sleep = float(val)
    user_temp[uid]['sleep'] = sleep
    
    # спросить комментарий
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Пропустить", callback_data="skip"))
    
    bot.edit_message_text(f"Сон: {sleep} ч \n\nКомментарий? (напиши или нажми кнопку)", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "skip")
def skip_comment(call):
    uid = call.from_user.id
    user_temp[uid]['comment'] = "-"
    finish_save(uid, call.message.chat.id)
    bot.edit_message_text("Сохранено!", call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    uid = message.from_user.id
    data = user_temp.get(uid, {})
    
    # это если ждём ввод часов работы
    if data.get('waiting') == 'work':
        try:
            work = float(message.text.replace(',', '.'))
            data['work'] = work
            data['waiting'] = None
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("6 ч", callback_data="s6"),
                types.InlineKeyboardButton("7 ч", callback_data="s7"),
                types.InlineKeyboardButton("8 ч", callback_data="s8"),
                types.InlineKeyboardButton("9 ч", callback_data="s9"),
                types.InlineKeyboardButton("Другое", callback_data="s_other"),
            )
            bot.send_message(message.chat.id, f"Работа: {work} ч \n\nСколько спал?", reply_markup=markup)
        except:
            bot.send_message(message.chat.id, "Введи число!")
        return
    
    # если ждём ввод часов сна
    if data.get('waiting') == 'sleep':
        try:
            sleep = float(message.text.replace(',', '.'))
            data['sleep'] = sleep
            data['waiting'] = None
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Пропустить", callback_data="skip"))
            bot.send_message(message.chat.id, f"Сон: {sleep} ч \n\nКомментарий?", reply_markup=markup)
        except:
            bot.send_message(message.chat.id, "Введи число!")
        return
    
    # если все данные собраны - комментарий
    if 'mood' in data and 'work' in data and 'sleep' in data:
        data['comment'] = message.text
        finish_save(uid, message.chat.id)
        bot.send_message(message.chat.id, "Сохранено с комментарием!")
        user_temp.pop(uid, None)
        return
    
    bot.send_message(message.chat.id, "Нажми /add чтобы начать")

def finish_save(uid, chat_id):
    """сохранить данные в базу"""
    data = user_temp.get(uid)
    if not data:
        return
    
    user_id = get_user_id(uid)
    if not user_id:
        add_user(uid, "user")
        user_id = get_user_id(uid)
    
    save_record(user_id, data['mood'], data['work'], data['sleep'], data.get('comment', '-'))
    user_temp.pop(uid, None)

# СТАТИСТИКА 

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    uid = message.from_user.id
    user_id = get_user_id(uid)
    
    if not user_id:
        bot.send_message(message.chat.id, "Сначала нажми /add")
        return
    
    records = get_all_records(user_id)
    if not records:
        bot.send_message(message.chat.id, "Нет данных")
        return
    
    # считаем среднее вручную (без pandas)
    moods = [r[1] for r in records]
    works = [r[2] for r in records]
    sleeps = [r[3] for r in records]
    
    avg_mood = sum(moods) / len(moods)
    avg_work = sum(works) / len(works)
    avg_sleep = sum(sleeps) / len(sleeps)
    
    text = "Статистика:\n\n"
    text += f"Дней записано: {len(records)}\n"
    text += f"Среднее настроение: {avg_mood:.1f}/5\n"
    text += f"Средняя работа: {avg_work:.1f} ч\n"
    text += f"Средний сон: {avg_sleep:.1f} ч\n"
    
    bot.send_message(message.chat.id, text)

# ИНСАТЙЫ

@bot.message_handler(commands=['insights'])
def insights_cmd(message):
    uid = message.from_user.id
    user_id = get_user_id(uid)
    
    if not user_id:
        bot.send_message(message.chat.id, "Нет данных")
        return
    
    records = get_all_records(user_id)
    if len(records) < 3:
        bot.send_message(message.chat.id, "Нужно хотя бы 3 дня данных")
        return
    
    # ищем закономерности
    good_sleep = []  # настроение когда спал 7+
    bad_sleep = []   # настроение когда спал меньше 7
    
    for r in records:
        if r[3] >= 7:
            good_sleep.append(r[1])
        else:
            bad_sleep.append(r[1])
    
    text = "Инсайты:\n\n"
    
    if good_sleep and bad_sleep:
        avg_good = sum(good_sleep) / len(good_sleep)
        avg_bad = sum(bad_sleep) / len(bad_sleep)
        
        if avg_good > avg_bad:
            text += f"Когда спишь 7+ часов, настроение лучше ({avg_good:.1f} против {avg_bad:.1f})\n"
        else:
            text += f"Интересненько — при малом сне настроение даже лучше ({avg_bad:.1f} против {avg_good:.1f})\n"
    
    # лучший и худший день
    best = max(records, key=lambda x: x[1])
    worst = min(records, key=lambda x: x[1])
    
    text += f"\n Лучший день: {best[0]} (настроение {best[1]}/5)\n"
    text += f" Худший день: {worst[0]} (настроение {worst[1]}/5)\n"
    
    bot.send_message(message.chat.id, text)

# ИСТОРИЯ

@bot.message_handler(commands=['history'])
def history_cmd(message):
    uid = message.from_user.id
    user_id = get_user_id(uid)
    
    if not user_id:
        bot.send_message(message.chat.id, "Нет данных")
        return
    
    records = get_all_records(user_id)[:10]  # последние 10
    
    if not records:
        bot.send_message(message.chat.id, "Пусто")
        return
    
    text = "История:\n\n"
    for r in records:
        text += f"{r[0]} | Настр: {r[1]} | Работа: {r[2]}ч | Сон: {r[3]}ч\n"
        if r[4] and r[4] != "-":
            text += f"    {r[4]}\n"
        text += "\n"
    
    bot.send_message(message.chat.id, text)

# ОЧИСТКА

@bot.message_handler(commands=['clear'])
def clear_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Да", callback_data="yes_clear"),
        types.InlineKeyboardButton("Нет", callback_data="no_clear"),
    )
    bot.send_message(message.chat.id, "Точно удалить все данные?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["yes_clear", "no_clear"])
def clear_callback(call):
    if call.data == "yes_clear":
        uid = call.from_user.id
        user_id = get_user_id(uid)
        if user_id:
            delete_records(user_id)
        bot.edit_message_text("️ Данные удалены", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("Отмена", call.message.chat.id, call.message.message_id)

# ЗАПУСК

if __name__ == "__main__":
    init_db()
    print("Бот запущен!")
    bot.infinity_polling()