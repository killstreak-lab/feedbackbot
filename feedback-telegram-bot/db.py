from peewee import *
from aiogram.types import Message
from prettytable import PrettyTable
from datetime import datetime
import csv
db = SqliteDatabase('users.db')

class User(Model):
    telegram_id = PrimaryKeyField()
    name = CharField(null=True)
    username = CharField(null=True)
    added_date = DateTimeField(default=datetime.now)

    class Meta:
        database = db

db.connect()
db.create_tables([User])

class DATABASE:
    @staticmethod
    async def send(message: Message) -> int:
        count = 0
        with db.atomic():
            for user in User.select():
                try:
                    await message.copy_to(user.telegram_id)
                    count += 1
                except Exception:
                    pass
        return count

    @staticmethod
    async def stats(message: Message) -> PrettyTable:
        table = PrettyTable(["Telegram ID", "Added Date", "Name", "Username"])
        with db.atomic():
            for user in User.select():
                table.add_row([user.telegram_id,
                               user.added_date.strftime("%Y-%m-%d %H:%M:%S"),
                               user.name,
                               user.username])
        return table

    @staticmethod
    async def save_user(telegram_id: int, name: str, username: str) -> bool:
        with db.atomic():
            user, created = User.get_or_create(telegram_id=telegram_id)
            if created:
                user.name = name
                user.username = username
                user.save()
        return created
