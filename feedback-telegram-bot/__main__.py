import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from configreader import load_config, Config
from commandsworker import set_bot_commands
from handlers.unsupported_reply import register_admin_reply_handler
from handlers.admin_no_reply import register_admin_no_reply_handlers
from handlers.usermode import register_usermode_handlers
from handlers.adminmode import register_adminmode_handlers
from handlers.bans import register_bans_handlers
from handlers.common import register_common_handlers
from updatesworker import get_handled_updates_list

from dotenv import load_dotenv
load_dotenv()

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    config: Config = load_config()
    if not config.bot.token:
        raise ValueError("Не указан токен. Бот не может быть запущен.")

    if not config.bot.admin_chat_id:
        raise ValueError("Не указан идентификатор чата для пересылки сообщений. Бот не может быть запущен.")
    if not isinstance(config.bot.admin_chat_id, int):
        raise ValueError(f'Идентификатор "{config.bot.admin_chat_id}" не является числом. Бот не может быть запущен.')

    bot = Bot(token=config.bot.token)

    if config.app.use_local_server is True:
        bot.server = TelegramAPIServer.from_base(config.app.local_server_host)

    bot["admin_chat_id"] = config.bot.admin_chat_id
    bot["remove_sent_confirmation"] = config.bot.remove_sent_confirmation
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_admin_reply_handler(dp, config.bot.admin_chat_id)
    register_bans_handlers(dp, config.bot.admin_chat_id)
    register_adminmode_handlers(dp, config.bot.admin_chat_id)
    register_admin_no_reply_handlers(dp, config.bot.admin_chat_id)
    register_common_handlers(dp)
    register_usermode_handlers(dp)

    await set_bot_commands(bot, config.bot.admin_chat_id)

    me = await bot.get_me()
    logging.info(f"Starting @{me.username}")
    
    print("Starting polling")
    await dp.reset_webhook()
    await dp.start_polling(allowed_updates=get_handled_updates_list(dp))
    await dp.storage.close()
    await dp.storage.wait_closed()
    await bot.session.close()

asyncio.run(main())
