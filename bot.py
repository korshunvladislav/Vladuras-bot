import asyncio
import logging
import sqlite3
import gspread

from aiogram import Bot, Dispatcher, types, html, F
from aiogram.filters import Command
from gspread import Client, Spreadsheet, Worksheet

from config_reader import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.bot_token.get_secret_value(), parse_mode="HTML")

dp = Dispatcher()

spreadsheets_url = "https://docs.google.com/spreadsheets/d/1GeQ58yEc_BMLnX0gB_nWt8ve7GO4Qj6HndqbFcfyNGk/edit?usp=sharing"

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


async def show_available_worksheets(sh: Spreadsheet):
    worksheets = sh.worksheets()

    for ws in worksheets:
        print("Worksheet with title", repr(ws.title), "and id", ws.id)


async def show_main_ws(sh: Spreadsheet):
    main_ws = sh.sheet1
    print("Main ws:", main_ws)


async def show_all_values_in_ws(ws: Worksheet):
    list_of_lists = ws.get_all_values()
    print(list_of_lists)
    print("===" * 20)
    for row in list_of_lists:
        print(row)
    myFile = open('output.txt', 'w')
    for element in list_of_lists:
        for i in range(len(element)):
            element[i] = element[i].center(55)
        myFile.write(str(element))
        myFile.write("\n")
    myFile.close()


async def main_spreadsheets():
    gc: Client = gspread.service_account("./service_account.json")
    sh: Spreadsheet = gc.open_by_url(spreadsheets_url)
    print(sh)
    ws = sh.sheet1
    await show_all_values_in_ws(ws)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await message.answer(f"Привет, {html.bold(user.first_name)}!")
    add_user(user.id, user.username, user.first_name, user.last_name)


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


@dp.message(Command("get_schedule"))
async def cmd_get_schedule(message: types.Message):
    await main_spreadsheets()
    await message.answer("👌")


@dp.message(F.text)
async def text_handling(message: types.Message):
    text = message.text
    user = message.from_user
    if "БИВ23" == text[:5] and len(text) == 6 and text[5] in '123456789':
        cursor.execute('UPDATE Users SET groupNumber = ? WHERE TelegramID = ?', (text, user.id))
        connection.commit()
        await message.answer(f"Теперь ваша группа {text}")
    elif "БИВ23" == text[:5] and len(text) == 6:
        await message.answer("Данной группы не существует")

    
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())