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

spreadsheets_url = config.url.get_secret_value()

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


async def check_user_exists(Telegram_id: int):
    cursor.execute('SELECT * FROM Users WHERE TelegramID = ?', (Telegram_id,))
    user = cursor.fetchone()
    return user is not None


async def set_group(GroupNumber: str, Telegram_id: str):
    cursor.execute('UPDATE Users SET groupNumber ? WHERE TelegramID = ?', (GroupNumber, Telegram_id))
    connection.commit()


async def get_group(Telegram_id: int):
    cursor.execute('SELECT groupNumber FROM Users WHERE TelegramID = ?', (Telegram_id,))
    result = cursor.fetchone()[0]
    return result


async def date_validation(date_string):
    try:
        date_object = dt.datetime.strptime(date_string, '%d.%m.%Y')
        return [True, date_object]
    except ValueError:
        try:
            date_object = dt.datetime.strptime(date_string, '%d.%m.%y')
            return [True, date_object]
        except ValueError:
            return [False, None]


async def check_schedule_available(file: json, date: dt.datetime):
    date_index = []
    offset = 0
    if date.isoweekday() == 6:
        date = date - dt.timedelta(days=1)
        offset = 29
    for i in range(len(file)):
        for j in range(len(file[i])):                
            if date.strftime('%d.%m.%Y') in file[i][j]:
                date_index.append(i + offset)
                date_index.append(j)
                break
        else:
            continue
        break
    if len(date_index) == 0:
        return [False, None]
    return [True, date_index]


async def find_group_index(file: json, groupNumber: str, date_index: int):
    group_index = -1
    for i in range(date_index, len(file[0])):
        if file[0][i] == groupNumber:
            group_index = i
            break
    return group_index


async def generate_schedule_message(file: json, date: dt.datetime, date_index: list, group_index: int):
    lectures = []
    for i in range(date_index[0], date_index[0] + 25, 4):
        temp_lect = []
        for j in range(4):
            temp_lect.append(file[i + j][group_index])
        temp_lect.insert(1, file[i][date_index[1] + 1])
        lectures.append(temp_lect)
    message_for_user = str()
    gap_count = 0
    for i in range(len(lectures)):
        if lectures[i][0] == "" and message_for_user != "":
            gap_count += 1
        else:
            if gap_count > 0:
                gap_hours = (gap_count * 80 + (gap_count + 1) * 20) // 60
                gap_minutes = (gap_count * 80 + (gap_count + 1) * 20) % 60
                message_for_user += html.bold(html.italic('Количество окон: ')) + str(gap_count) + '\n'
                message_for_user += html.italic('Общее время перерыва: ') + str(gap_hours) + ' ч ' + str(gap_minutes) + ' мин\n\n'
                gap_count = 0
            if lectures[i][0] != "":
                message_for_user += html.italic('Предмет: ') + lectures[i][0] + '\n' + \
                                    html.italic('Время: ') + lectures[i][1] + '\n' + \
                                    html.italic('Тип пары: ') + lectures[i][2] + '\n' + \
                                    html.italic('Преподаватель: ') + lectures[i][3] + '\n' + \
                                    html.italic('Аудитория: ') + lectures[i][4] + '\n\n'
    return message_for_user


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
    gc: Client = gspread.service_account()
    sh: Spreadsheet = gc.open_by_url(spreadsheets_url)
    print(sh)
    ws = sh.sheet1
    await show_all_values_in_ws(ws)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await message.answer(f"Привет, {html.bold(user.first_name)}!")
    if not await check_user_exists(user.id):
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
    if message.from_user.id == int(config.owner_id.get_secret_value()):
        await main_spreadsheets()
        await message.answer("Файл успешно создан")
    else:
        await message.answer("Отказано в доступе")


@dp.message(Command("get_schedule"))
async def cmd_get_schedule(message: types.Message, command: CommandObject):
    groupNumber = await get_group(message.from_user.id)
    if groupNumber is None:
        await message.answer("Чтобы пользоваться этой командой, укажите свою группу с помощью команды /set_group")
        return
    if command.args is None:
        date = dt.datetime.today()
    else:
        date_object = await date_validation(command.args)
        if date_object[0]:
            date = date_object[1]
        else:
            await message.answer("Неверный формат даты")
            return
    with open('data.json', 'r') as file:
        schedule_file = json.load(file)
    schedule_check_result = await check_schedule_available(schedule_file, date)
    if schedule_check_result[0]:
        date_index = schedule_check_result[1]
    else:
        await message.answer("Расписания на этот день пока нет")
        return
    group_index = await find_group_index(schedule_file, groupNumber, date_index[1])
    if group_index == -1:
        await message.answer("Расписание для вашей группы не найдено")
        return
    await message.answer(await generate_schedule_message(schedule_file, date, date_index, group_index))


@dp.message(F.text)
async def text_handling(message: types.Message):
    text = message.text
    user = message.from_user
    if "БИВ23" == text[:5] and len(text) == 6 and text[5] in '123456789':
        await set_group(user.id, text)
        await message.answer(f"Теперь ваша группа {text}")
    elif "БИВ23" == text[:5] and len(text) == 6:
        await message.answer("Данной группы не существует")

    
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())