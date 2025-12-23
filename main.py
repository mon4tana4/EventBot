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