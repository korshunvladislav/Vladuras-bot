import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, types, html, F
from aiogram.filters import Command, CommandObject
from datetime import datetime

from config_reader import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.bot_token.get_secret_value(), parse_mode="HTML")

dp = Dispatcher()

connection = sqlite3.connect("database.db")
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
id INTEGER PRIMARY KEY,
TelegramID INTEGER NOT NULL,
username TEXT NOT NULL,
firstName TEXT,
lastName TEXT,
groupNumber TEXT
)
''')

connection.commit()

def add_user(Telegram_id: int, Username: str, FirstName: str, LastName: str):
    cursor.execute('INSERT INTO Users (TelegramID, username, firstName, lastName) VALUES (?, ?, ?, ?)', (Telegram_id, Username, FirstName, LastName))
    connection.commit()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {html.bold(message.from_user.first_name)}!")
    add_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())