from aiogram import Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import IsReplyFilter, IDFilter
from aiogram.utils.exceptions import BotBlocked, TelegramAPIError
from .state import *
from db import *
import os

def extract_id(message: types.Message) -> int:
    entities = message.reply_to_message.entities or message.reply_to_message.caption_entities

    hashtag = entities[-1].get_text(message.reply_to_message.text or message.reply_to_message.caption)
    if len(hashtag) < 4 or not hashtag[3:].isdigit(): 
        raise ValueError("Некорректный ID для ответа!")

    return hashtag[3:]


async def reply_to_user(message: types.Message):
    """
    Ответ администратора на сообщение юзера (отправленное ботом).
    Используется метод copy_message, поэтому ответить можно чем угодно, хоть опросом.

    :param message: сообщение от админа, являющееся ответом на другое сообщение
    """

    try:
        user_id = extract_id(message)
    except ValueError as ex:
        return await message.reply(str(ex))

    try:
        await message.copy_to(user_id)
    except BotBlocked:
        await message.reply("Не удалось отправить сообщение адресату, т.к. бот заблокирован на их стороне")
    except TelegramAPIError as ex:
        await message.reply(f"Не удалось отправить сообщение адресату! Ошибка: {ex}")


async def get_user_info(message: types.Message):
    try:
        user_id = extract_id(message)
    except ValueError as ex:
        return await message.reply(str(ex))
    try:
        user = await message.bot.get_chat(user_id)
    except TelegramAPIError as ex:
        return await message.reply(f"Не удалось получить информацию о пользователе! Ошибка: {ex}")
    u = f"@{user.username}" if user.username else 'нет'
    await message.reply(f"Имя: {user.full_name}\n\nID: {user.id}\nUsername: {u}")


async def admin_help(message: types.Message):
    await message.answer("В настоящий момент доступны следующие команды администратора:\n\n"
                         "/get или /who (в ответ на сообщение) — запрос информации о пользователе по его ID.")


def register_adminmode_handlers(dp: Dispatcher, admin_chat_id: int):
    @dp.message_handler(commands=['send'])
    async def send_to_all(message: Message):
        await message.answer(
                'Введите текст сообщения', 
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton(text='❌ Отмена', callback_data='cancel', parse_mode="HTML")))
        await UserState.alls.set()

    @dp.message_handler(state=UserState.alls)
    async def send_us(message: Message, state: FSMContext):
        await message.answer('Отправка началась')
        await state.finish()

        try:
            result = await DATABASE.send(message)
            await message.answer(f'Отправлено {result} пользователям')
        except Exception as e:
            await message.answer(f'Ошибка при отправке сообщения: {e}')

    @dp.callback_query_handler(lambda c: c.data == 'cancel', state=UserState.alls)
    async def dont_send_us(call: CallbackQuery, state: FSMContext):
        await call.answer()
        await call.message.answer('Отменено')
        await state.finish()

    @dp.message_handler(commands=["stats"])
    async def stats_handler(message: Message):
        table = await DATABASE.stats(message)
        user_count = User.select().count()

        with open("users.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(table.field_names)
            for row in table:
                writer.writerow(row)

        with open("users.csv", "rb") as f:
            await message.answer_document(f, caption=f"Количество пользователей: <code>{user_count}</code>", parse_mode="HTML")
        
        os.remove("users.csv")

    dp.register_message_handler(get_user_info, IsReplyFilter(is_reply=True), IDFilter(chat_id=admin_chat_id),
                                commands=["get", "who"])
    dp.register_message_handler(admin_help, IDFilter(chat_id=admin_chat_id), commands="help")
    dp.register_message_handler(reply_to_user, IsReplyFilter(is_reply=True), IDFilter(chat_id=admin_chat_id),
                                content_types=types.ContentTypes.ANY)
