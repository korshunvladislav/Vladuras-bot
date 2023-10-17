import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, types, html, F
from aiogram.filters import Command

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


async def add_user(Telegram_id: int, Username: str, FirstName: str, LastName: str):
    cursor.execute('INSERT INTO Users (TelegramID, username, firstName, lastName) VALUES (?, ?, ?, ?)', (Telegram_id, Username, FirstName, LastName))
    connection.commit()


async def set_group(GroupNumber: str, Username: str):
    cursor.execute('UPDATE Users SET groupNumber ? WHERE username = ?', (GroupNumber, Username))
    connection.commit()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {html.bold(message.from_user.first_name)}!")
    add_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)


@dp.message(Command("set_group"))
async def cmd_set_group(message: types.Message):
    kb = list()
    for i in range(3):
        buf = list()
        for j in range(3):
            buf.append(types.KeyboardButton(text=f"БИВ23{i * 3 + j + 1}"))
        kb.append(buf)
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Выберите номер вашей группы"
    )
    await message.answer("В какой вы группе?", reply_markup=keyboard)


@dp.message(F.text)
async def text_handling(message: types.Message):
    text = message.text
    user = message.from_user
    if "БИВ23" == text[:5] and len(text) == 6 and text[5] in '123456789':
        cursor.execute('UPDATE Users SET groupNumber = ? WHERE TelegramID = ?', (text, user.id))
        connection.commit()
        await message.answer(f"Теперь ваша группа {text}")

    
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())