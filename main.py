"""Лабораторная работа номер 4"""

import os
import json
import telebot
from telebot import types
from datetime import datetime, date, timedelta
import re

BOT_TOKEN = "8320022661:AAHEf6qV60tVXSJ3fDi7KhpviMU2cUM3ihM"

bot = telebot.TeleBot(BOT_TOKEN)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")

# Хранилище состояний пользователей
user_states = {}


def load_events():
    try:
        if os.path.exists(EVENTS_FILE):
            with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        return {}
    return {}


def save_events(events):
    try:
        with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
    except:
        pass


def get_user_events(user_id):
    events = load_events()
    return events.get(str(user_id), [])


def save_user_events(user_id, events_list):
    events = load_events()
    events[str(user_id)] = events_list
    save_events(events)


def get_next_event_id(user_id):
    events = get_user_events(user_id)
    if not events:
        return 1
    return max(event.get('id', 0) for event in events) + 1


def parse_date(date_str):
    try:
        date_str = date_str.strip().replace('/', '.')

        if date_str.count('.') == 1:
            day, month = map(int, date_str.split('.'))
            today = date.today()
            event_date = date(today.year, month, day)
            if event_date < today:
                event_date = date(today.year + 1, month, day)

        elif date_str.count('.') == 2:
            day, month, year = map(int, date_str.split('.'))
            if year < 100:
                year += 2000
            event_date = date(year, month, day)
        else:
            return None

        return event_date

    except:
        return None


def parse_time(time_str):
    try:
        time_str = time_str.strip().lower()

        if time_str in ['весь день', 'целый день', 'день']:
            return "00:00"

        time_str = time_str.replace(':', '').replace('.', '')

        if len(time_str) == 4 and time_str.isdigit():
            hours = int(time_str[:2])
            minutes = int(time_str[2:])
            if 0 <= hours < 24 and 0 <= minutes < 60:
                return f"{hours:02d}:{minutes:02d}"

        if ':' in time_str:
            hours, minutes = map(int, time_str.split(':'))
            if 0 <= hours < 24 and 0 <= minutes < 60:
                return f"{hours:02d}:{minutes:02d}"

    except:
        pass

    return None


def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📅 Новое событие", "📋 Мои события")
    keyboard.row("🗑 Удалить", "📊 Сегодня")
    keyboard.row("ℹ️ Помощь")
    return keyboard


@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для планирования событий.\n\n"
        "Используйте кнопки ниже:",
        reply_markup=create_main_keyboard()
    )


@bot.message_handler(commands=['help'])
@bot.message_handler(func=lambda message: message.text == 'ℹ️ Помощь')
def help_command(message):
    help_text = (
        "📚 Основные команды:\n\n"
        "/new - Новое событие\n"
        "/list - Все события\n"
        "/today - События сегодня\n"
        "/delete - Удалить событие\n"
        "/help - Эта справка\n\n"
        "Или используйте кнопки ниже 👇"
    )
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['new'])
@bot.message_handler(func=lambda message: message.text == '📅 Новое событие')
def new_event_start(message):
    user_id = str(message.chat.id)
    user_states[user_id] = {'step': 'waiting_title'}

    msg = bot.send_message(
        message.chat.id,
        "Введите название события:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_title)


def process_title(message):
    user_id = str(message.chat.id)

    if len(message.text) < 2:
        msg = bot.send_message(message.chat.id, "❌ Название слишком короткое. Введите название:")
        bot.register_next_step_handler(msg, process_title)
        return

    user_states[user_id] = {
        'step': 'waiting_description',
        'title': message.text
    }

    msg = bot.send_message(message.chat.id, "Введите описание (или '-' если не нужно):")
    bot.register_next_step_handler(msg, process_description)


def process_description(message):
    user_id = str(message.chat.id)

    description = message.text if message.text != '-' else ""
    user_states[user_id]['step'] = 'waiting_date'
    user_states[user_id]['description'] = description

    msg = bot.send_message(message.chat.id, "Введите дату (ДД.ММ.ГГГГ или ДД.ММ):")
    bot.register_next_step_handler(msg, process_date_step)


def process_date_step(message):
    user_id = str(message.chat.id)

    parsed_date = parse_date(message.text)

    if not parsed_date:
        msg = bot.send_message(message.chat.id, "❌ Неверный формат даты. Введите ДД.ММ.ГГГГ или ДД.ММ:")
        bot.register_next_step_handler(msg, process_date_step)
        return

    today = date.today()
    if parsed_date < today:
        msg = bot.send_message(message.chat.id, "❌ Дата не может быть в прошлом. Введите будущую дату:")
        bot.register_next_step_handler(msg, process_date_step)
        return

    user_states[user_id]['step'] = 'waiting_time'
    user_states[user_id]['event_date'] = parsed_date.isoformat()

    msg = bot.send_message(message.chat.id, "Введите время (ЧЧ:ММ или 'весь день'):")
    bot.register_next_step_handler(msg, process_time_step)


def process_time_step(message):
    user_id = str(message.chat.id)

    parsed_time = parse_time(message.text)

    if not parsed_time:
        msg = bot.send_message(message.chat.id, "❌ Неверный формат времени. Введите ЧЧ:ММ или 'весь день':")
        bot.register_next_step_handler(msg, process_time_step)
        return

    data = user_states.get(user_id, {})

    events = get_user_events(user_id)
    event_id = get_next_event_id(user_id)

    full_date = f"{data['event_date']} {parsed_time}:00" if parsed_time != "00:00" else f"{data['event_date']} 00:00:00"

    events.append({
        'id': event_id,
        'title': data['title'],
        'description': data.get('description', ''),
        'date': full_date,
        'time': parsed_time,
        'created': datetime.now().isoformat()
    })

    save_user_events(user_id, events)

    display_date = datetime.fromisoformat(data['event_date']).strftime('%d.%m.%Y')
    time_display = "весь день" if parsed_time == "00:00" else parsed_time

    # ВОТ ЭТО ИСПРАВЛЯЕМ - возвращаем полную клавиатуру
    bot.send_message(
        message.chat.id,
        f"✅ Событие создано!\n\n"
        f"📅 {data['title']}\n"
        f"📝 {data.get('description', 'нет описания')}\n"
        f"⏰ {display_date} ({time_display})\n"
        f"🆔 ID: {event_id}",
        reply_markup=create_main_keyboard()  # ВОТ ЗДЕСЬ ВОЗВРАЩАЕМ ПОЛНУЮ КЛАВИАТУРУ
    )

    if user_id in user_states:
        del user_states[user_id]


@bot.message_handler(commands=['list'])
@bot.message_handler(func=lambda message: message.text == '📋 Мои события')
def list_events(message):
    user_id = str(message.chat.id)
    events = get_user_events(user_id)

    if not events:
        bot.send_message(message.chat.id, "📭 Нет событий.")
        return

    events.sort(key=lambda x: x.get('date', ''))

    text = f"📋 Ваши события ({len(events)}):\n\n"

    for event in events[:10]:
        try:
            dt = datetime.fromisoformat(event['date'])
            date_str = dt.strftime('%d.%m.%Y')
            time_str = "" if event.get('time') == '00:00' else f" {dt.strftime('%H:%M')}"
        except:
            date_str = event.get('date', '')
            time_str = ""

        text += f"• {event['title']} - {date_str}{time_str} (ID: {event['id']})\n"

    if len(events) > 10:
        text += f"\n... и еще {len(events) - 10}"

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['today'])
@bot.message_handler(func=lambda message: message.text == '📊 Сегодня')
def today_events(message):
    user_id = str(message.chat.id)
    events = get_user_events(user_id)

    if not events:
        bot.send_message(message.chat.id, "📭 Нет событий на сегодня.")
        return

    today = datetime.now().date()
    today_events_list = []

    for event in events:
        try:
            event_date = datetime.fromisoformat(event['date']).date()
            if event_date == today:
                today_events_list.append(event)
        except:
            continue

    if today_events_list:
        text = f"📅 Сегодня ({today.strftime('%d.%m.%Y')}):\n\n"
        for event in today_events_list:
            time_str = event.get('time', '00:00')
            text += f"• {event['title']} - {time_str if time_str != '00:00' else 'весь день'}\n"
    else:
        text = f"📅 На сегодня ({today.strftime('%d.%m.%Y')}) событий нет."

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['delete'])
@bot.message_handler(func=lambda message: message.text == '🗑 Удалить')
def delete_event(message):
    user_id = str(message.chat.id)
    events = get_user_events(user_id)

    if not events:
        bot.send_message(message.chat.id, "Нет событий для удаления.")
        return

    text = "🗑 Введите ID события для удаления:\n\n"

    for event in events[:5]:
        try:
            dt = datetime.fromisoformat(event['date'])
            date_str = dt.strftime('%d.%m')
        except:
            date_str = event.get('date', '')[:5]

        text += f"🆔 {event['id']} - {event['title'][:20]}... ({date_str})\n"

    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, process_delete)


def process_delete(message):
    user_id = str(message.chat.id)

    try:
        event_id = int(message.text)
        events = get_user_events(user_id)

        for i, event in enumerate(events):
            if event.get('id') == event_id:
                del events[i]
                save_user_events(user_id, events)
                bot.send_message(message.chat.id, f"✅ Событие #{event_id} удалено!")
                return

        bot.send_message(message.chat.id, f"❌ Событие #{event_id} не найдено.")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите числовой ID.")


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = str(message.chat.id)

    if user_id in user_states:
        state = user_states[user_id].get('step')

        if state == 'waiting_title':
            process_title(message)
        elif state == 'waiting_description':
            process_description(message)
        elif state == 'waiting_date':
            process_date_step(message)
        elif state == 'waiting_time':
            process_time_step(message)
        return

    pattern = r'^(\d{1,2})\.(\d{1,2})\s+(.+)'
    match = re.match(pattern, message.text)

    if match:
        try:
            day, month, rest = match.groups()
            day, month = int(day), int(month)
            year = datetime.now().year

            event_date = date(year, month, day)
            today = date.today()

            if event_date >= today:
                parts = rest.split(' ', 1)
                title = parts[0]
                description = parts[1] if len(parts) > 1 else ""

                events = get_user_events(user_id)
                event_id = get_next_event_id(user_id)

                events.append({
                    'id': event_id,
                    'title': title,
                    'description': description,
                    'date': event_date.isoformat(),
                    'time': "00:00",
                    'created': datetime.now().isoformat()
                })

                save_user_events(user_id, events)

                bot.send_message(
                    message.chat.id,
                    f"✅ Событие создано!\n"
                    f"📅 {title}\n"
                    f"🆔 ID: {event_id}"
                )
        except:
            pass


if __name__ == "__main__":
    print("🚀 Бот запущен...")
    bot.polling(none_stop=True)