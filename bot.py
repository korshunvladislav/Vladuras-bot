import asyncio
import logging
import sqlite3
import gspread
import datetime as dt
import json

from aiogram import Bot, Dispatcher, types, html, F
from aiogram.filters import Command, CommandObject
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


async def get_group(Telegram_id):
    cursor.execute('SELECT groupNumber FROM Users WHERE TelegramID = ?', (Telegram_id,))
    result = cursor.fetchall()[0][0]
    return result


async def is_valid_date(date_string):
    try:
        datetime_object = dt.datetime.strptime(date_string, '%d.%m.%Y')
        return True
    except ValueError:
        return False
    

async def show_available_worksheets(sh: Spreadsheet):
    worksheets = sh.worksheets()

    for ws in worksheets:
        print("Worksheet with title", repr(ws.title), "and id", ws.id)


async def show_main_ws(sh: Spreadsheet):
    main_ws = sh.sheet1
    print("Main ws:", main_ws)


async def show_all_values_in_ws(ws: Worksheet):
    list_of_lists = ws.get_all_values()
    with open('data.json', 'w') as file:
        json.dump(list_of_lists, file, ensure_ascii=False)
    with open('formatted_output.txt', 'w') as formatted_file:
        for element in list_of_lists:
            for i in range(len(element)):
                element[i] = element[i].replace(" \nсеминар\nЕрохина", "").center(55)
            formatted_file.write(str(element))
            formatted_file.write("\n")


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


@dp.message(Command("generate_file"))
async def cmd_generate_file(message: types.Message):
    await main_spreadsheets()
    await message.answer("Файл успешно создан")


@dp.message(Command("get_schedule"))
async def cmd_get_schedule(message: types.Message, command: CommandObject):
    groupNumber = await get_group(message.from_user.id)
    with open('data.json', 'r') as file:
        loaded_list_of_lists = json.load(file)
    if command.args is None:
        date = dt.date.today().strftime("%d.%m.%Y")
        await message.answer("Расписание на сегодня:")
    else:
        if await is_valid_date(command.args):
            date = dt.datetime.strptime(command.args, '%d.%m.%Y').strftime("%d.%m.%Y")
            await message.answer(f"Расписание на {date}:")
        else:
            await message.answer("Неверный формат даты")
            return
    date_index = []
    for i in range(len(loaded_list_of_lists)):
        for j in range(len(loaded_list_of_lists[i])):                
            if date in loaded_list_of_lists[i][j]:
                date_index.append(i)
                date_index.append(j)
                break
        else:
            continue
        break
    group_index = -1
    for i in range(date_index[1], len(loaded_list_of_lists[0])):
        if loaded_list_of_lists[0][i] == groupNumber:
            group_index = i
            break
    lectures = []
    for i in range(date_index[0], date_index[0] + 25, 4):
        temp_lect = []
        for j in range(4):
            temp_lect.append(loaded_list_of_lists[i + j][group_index])
        temp_lect.insert(1, loaded_list_of_lists[i][date_index[1] + 1])
        lectures.append(temp_lect)
    await message.answer(str(lectures))
    message_for_user = ""
    gap_count = 0
    for i in range(len(lectures)):
        if lectures[i][0] == "" and message_for_user != "":
            gap_count += 1
        else:
            if gap_count > 0:
                message_for_user += f"{html.bold(html.italic('Количество окон:'))} {gap_count}\n"
                message_for_user += f"{html.italic('Общее время перерыва:')} {(gap_count * 80 + (gap_count + 1) * 20) // 60} ч {(gap_count * 80 + (gap_count + 1) * 20) % 60} мин\n\n"
                gap_count = 0
            if lectures[i][0] != "":
                message_for_user += f"{html.italic('Предмет:')} {lectures[i][0]}\n{html.italic('Время:')} {lectures[i][1]}\n{html.italic('Тип пары:')} {lectures[i][2]}\n{html.italic('Преподаватель:')} {lectures[i][3]}\n{html.italic('Аудитория:')} {lectures[i][4]}\n\n"
    await message.answer(message_for_user)


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