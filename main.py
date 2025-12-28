"""Лабораторная работа номер 4"""

import os
import json
import asyncio
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8320022661:AAHEf6qV60tVXSJ3fDi7KhpviMU2cUM3ihM"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


class EventStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_date = State()
    waiting_time = State()


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


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    keyboard = [
        [types.KeyboardButton(text="📅 Новое событие")],
        [types.KeyboardButton(text="📋 Мои события")],
        [types.KeyboardButton(text="🗑 Удалить")],
        [types.KeyboardButton(text="ℹ️ Помощь")]
    ]

    await message.answer(
        "👋 Привет! Я бот для планирования событий.\n\n"
        "Используйте кнопки ниже:",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )


@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "📚 Основные команды:\n\n"
        "/new - Новое событие\n"
        "/list - Все события\n"
        "/today - События сегодня\n"
        "/delete - Удалить событие\n"
        "/help - Эта справка"
    )


@dp.message(Command("new"))
@dp.message(F.text == "📅 Новое событие")
async def new_event_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название события:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(EventStates.waiting_title)


@dp.message(EventStates.waiting_title)
async def process_title(message: types.Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("❌ Название слишком короткое. Введите название:")
        return

    await state.update_data(title=message.text)
    await message.answer("Введите описание (или '-' если не нужно):")
    await state.set_state(EventStates.waiting_description)


@dp.message(EventStates.waiting_description)
async def process_description(message: types.Message, state: FSMContext):
    description = message.text if message.text != '-' else ""
    await state.update_data(description=description)
    await message.answer("Введите дату (ДД.ММ.ГГГГ или ДД.ММ):")
    await state.set_state(EventStates.waiting_date)


@dp.message(EventStates.waiting_date)
async def process_date(message: types.Message, state: FSMContext):
    parsed_date = parse_date(message.text)

    if not parsed_date:
        await message.answer("❌ Неверный формат даты. Введите ДД.ММ.ГГГГ или ДД.ММ:")
        return

    today = date.today()
    if parsed_date < today:
        await message.answer("❌ Дата не может быть в прошлом. Введите будущую дату:")
        return

    await state.update_data(event_date=parsed_date.isoformat())
    await message.answer("Введите время (ЧЧ:ММ или 'весь день'):")
    await state.set_state(EventStates.waiting_time)


@dp.message(EventStates.waiting_time)
async def process_time(message: types.Message, state: FSMContext):
    parsed_time = parse_time(message.text)

    if not parsed_time:
        await message.answer("❌ Неверный формат времени. Введите ЧЧ:ММ или 'весь день':")
        return

    data = await state.get_data()
    user_id = str(message.from_user.id)
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

    await message.answer(
        f"✅ Событие создано!\n\n"
        f"📅 {data['title']}\n"
        f"📝 {data.get('description', 'нет описания')}\n"
        f"⏰ {display_date} ({time_display})\n"
        f"🆔 ID: {event_id}",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="📋 Мои события")]],
                                               resize_keyboard=True)
    )

    await state.clear()


@dp.message(Command("list"))
@dp.message(F.text == "📋 Мои события")
async def list_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    events = get_user_events(user_id)

    if not events:
        await message.answer("📭 Нет событий.")
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

    await message.answer(text)


@dp.message(Command("today"))
async def today_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    events = get_user_events(user_id)

    if not events:
        await message.answer("📭 Нет событий на сегодня.")
        return

    today = datetime.now().date()
    today_events = []

    for event in events:
        try:
            event_date = datetime.fromisoformat(event['date']).date()
            if event_date == today:
                today_events.append(event)
        except:
            continue

    if today_events:
        text = f"📅 Сегодня ({today.strftime('%d.%m.%Y')}):\n\n"
        for event in today_events:
            time_str = event.get('time', '00:00')
            text += f"• {event['title']} - {time_str if time_str != '00:00' else 'весь день'}\n"
    else:
        text = f"📅 На сегодня ({today.strftime('%d.%m.%Y')}) событий нет."

    await message.answer(text)


@dp.message(Command("delete"))
@dp.message(F.text == "🗑 Удалить")
async def delete_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    events = get_user_events(user_id)

    if not events:
        await message.answer("Нет событий для удаления.")
        return

    text = "🗑 Введите ID события для удаления:\n\n"

    for event in events[:5]:
        try:
            dt = datetime.fromisoformat(event['date'])
            date_str = dt.strftime('%d.%m')
        except:
            date_str = event.get('date', '')[:5]

        text += f"🆔 {event['id']} - {event['title'][:20]}... ({date_str})\n"

    await message.answer(text)


@dp.message(F.text.regexp(r'^\d+$'))
async def delete_by_id(message: types.Message):
    try:
        event_id = int(message.text)
        user_id = str(message.from_user.id)
        events = get_user_events(user_id)

        for i, event in enumerate(events):
            if event.get('id') == event_id:
                del events[i]
                save_user_events(user_id, events)
                await message.answer(f"✅ Событие #{event_id} удалено!")
                return

        await message.answer(f"❌ Событие #{event_id} не найдено.")

    except ValueError:
        await message.answer("❌ Введите числовой ID.")


@dp.message(F.text)
async def quick_create(message: types.Message):
    import re
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

                user_id = str(message.from_user.id)
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

                await message.answer(
                    f"✅ Событие создано!\n"
                    f"📅 {title}\n"
                    f"🆔 ID: {event_id}"
                )
        except:
            pass


async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())