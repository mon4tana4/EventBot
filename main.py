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