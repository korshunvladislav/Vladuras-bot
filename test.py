# @dp.message(Command("name"))
# async def cmd_name(message: types.Message, command: CommandObject):
#     if command.args:
#         await message.answer(f"Привет, {html.bold(html.quote(command.args))}!")
#     else:
#         await message.answer("Имя своё черкани после команды /name!")
    

# @dp.message(F.text)
# async def echo_with_time(message: types.Message):
#     time_now = datetime.now().strftime('%H:%M')
#     added_text = html.underline(f"Создано в {time_now}")
#     await message.answer(f"{message.html_text}\n\n{added_text}")
