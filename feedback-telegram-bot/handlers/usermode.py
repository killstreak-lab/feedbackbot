from asyncio import create_task, sleep
from aiogram import Dispatcher, types
from aiogram.types import ContentType, Message, ParseMode

from blocklists import banned, shadowbanned
from db import *

async def _send_expiring_notification(message: types.Message):
    """
    Отправляет "самоуничтожающееся" через 5 секунд сообщение

    :param message: сообщение, на которое бот отвечает подтверждением отправки
    """
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    await DATABASE.save_user(telegram_id, first_name, username)
    remove_sent_confirmation = message.bot.get("remove_sent_confirmation")
    msg = await message.reply("Сообщение отправлено!")
    if remove_sent_confirmation:
        await sleep(5.0)
        await msg.delete()


async def text_message(message: types.Message):
    """
    Хэндлер на текстовые сообщения от пользователя

    :param message: сообщение от пользователя для админа(-ов)
    """
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    await DATABASE.save_user(telegram_id, first_name, username)
    if len(message.text) > 4000:
        return await message.reply("К сожалению, длина этого сообщения превышает допустимый размер. "
                                   "Пожалуйста, сократи свою мысль и попробуй ещё раз.")
    admin_chat_id = message.bot.get("admin_chat_id")

    if message.from_user.id in banned:
        await message.answer("К сожалению, ты был заблокирован автором бота и твои сообщения не будут доставлены.")
    elif message.from_user.id in shadowbanned:
        return
    else:
        await message.bot.send_message(
            admin_chat_id, f"<b>#Сообщение</b> <a href='tg://user?id={telegram_id}'>{first_name}</a>:\n\n{message.html_text}\n\n#id{message.from_user.id}", parse_mode="HTML"
        )
        await create_task(_send_expiring_notification(message))


async def supported_media(message: types.Message):
    """
    Хэндлер на медиафайлы от пользователя.
    Поддерживаются только типы, к которым можно добавить подпись (полный список см. в регистраторе внизу)

    :param message: медиафайл от пользователя
    """
    telegram_id = message.from_user.id
    if not User.select().where(User.telegram_id == telegram_id).exists():
        User.create(telegram_id=telegram_id)
    if message.caption and len(message.caption) > 1000:
        return await message.reply("К сожалению, длина подписи медиафайла превышает допустимый размер. "
                                   "Пожалуйста, сократи свою мысль и попробуй ещё раз.")
    admin_chat_id = message.bot.get("admin_chat_id")
    await message.copy_to(admin_chat_id,
                          caption=((message.caption or "") + f"\n\n#id{message.from_user.id}"),
                          parse_mode="HTML")
    await create_task(_send_expiring_notification(message))


async def unsupported_types(message: types.Message):
    """
    Хэндлер на неподдерживаемые типы сообщений, т.е. те, к которым нельзя добавить подпись

    :param message: сообщение от пользователя
    """
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    await DATABASE.save_user(telegram_id, first_name, username)
    if message.content_type not in (
            ContentType.NEW_CHAT_MEMBERS, ContentType.LEFT_CHAT_MEMBER, ContentType.VOICE_CHAT_STARTED,
            ContentType.VOICE_CHAT_ENDED, ContentType.VOICE_CHAT_PARTICIPANTS_INVITED,
            ContentType.MESSAGE_AUTO_DELETE_TIMER_CHANGED, ContentType.NEW_CHAT_PHOTO, ContentType.DELETE_CHAT_PHOTO,
            ContentType.SUCCESSFUL_PAYMENT, ContentType.PROXIMITY_ALERT_TRIGGERED,
            ContentType.NEW_CHAT_TITLE, ContentType.PINNED_MESSAGE):
        await message.reply("К сожалению, этот тип сообщения не поддерживается "
                            "для пересылки от пользователей. Отправь что-нибудь другое.")


async def cmd_help_user(message: types.Message):
    """
    Справка для пользователя

    :param message: сообщение от пользователя с командой /help
    """
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    await DATABASE.save_user(telegram_id, first_name, username)
    await message.answer(
        "С помощью этого бота ты можешь связаться с админом @Lifeinsomniaaa (t.me/+Fz0pEJNfkyI4YTcy).\n"
        "Поддерживаются почти все типы сообщений, а именно: текст, фото, видео, аудио, файлы и голосовые сообщения.")


async def cmd_start_user(message: types.Message):
    """
    Приветственное сообщение от бота пользователю

    :param message: сообщение от пользователя с командой /start
    """
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    user_link = f"<a href='tg://user?id={telegram_id}'>{first_name}</a>"

    if await DATABASE.save_user(telegram_id, first_name, username):
        admin_chat_id = message.bot.get("admin_chat_id")
        await message.bot.send_message(
            admin_chat_id, 
            text=f'🔔 #НовыйПользователь\n\n'
                f'<b>👤 User:</b> {user_link}\n'
                f'<b>🆔 Telegram ID:</b> {telegram_id}\n'
                f'<b>🆔 Username:</b> {username}',
            parse_mode=ParseMode.HTML)
    
    await message.answer(
        f"Здравствуйте, {user_link}!\n"
        "Напишите ваш вопрос и мы ответим Вам в ближайшее время.",
        parse_mode=ParseMode.HTML)

def register_usermode_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start_user, commands="start")
    dp.register_message_handler(cmd_help_user, commands="help")
    dp.register_message_handler(text_message, content_types=ContentType.TEXT)
    dp.register_message_handler(supported_media, content_types=[
        ContentType.ANIMATION, ContentType.AUDIO, ContentType.PHOTO,
        ContentType.DOCUMENT, ContentType.VIDEO, ContentType.VOICE
    ])
    dp.register_message_handler(unsupported_types, content_types=ContentType.ANY)
