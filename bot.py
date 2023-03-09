# aiogram            2.25.1    Is a pretty simple and fully asynchronous framework for Telegram Bot API
# aiogram-dialog     1.9.0     Mini-framework for dialogs on top of aiogram
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram_dialog import (
    Dialog, DialogManager, DialogRegistry,
    ChatEvent, StartMode, Window,
)
from aiogram_dialog.manager.protocols import ManagedDialogAdapterProto
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Back, Button, Row, Select, SwitchTo
from aiogram_dialog.widgets.managed import ManagedWidgetAdapter
from aiogram_dialog.widgets.text import Const, Format, Multi

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.DEBUG,
    format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
)


class DialogSG(StatesGroup):
    greeting = State()
    age = State()
    finish = State()


async def get_data(dialog_manager: DialogManager, **kwargs):
    ctx = dialog_manager.current_context()
    age = ctx.dialog_data.get("age", None)
    return {
        "name": ctx.dialog_data.get("name", ""),
        "age": age,
        "can_smoke": age in ("18-25", "25-40", "40+"),
    }


async def name_handler(message: Message, dialog: ManagedDialogAdapterProto, manager: DialogManager):
    ctx = manager.current_context()
    if manager.is_preview():
        await dialog.next()
        return
    ctx.dialog_data["name"] = message.text
    await message.answer(f"Nice to meet you, {message.text}")
    await dialog.next()


async def other_type_handler(message: Message, dialog: ManagedDialogAdapterProto, manager: DialogManager):
    await message.answer("Text is expected")


async def on_finish(callback: CallbackQuery, button: Button,
                    manager: DialogManager):
    if manager.is_preview():
        await manager.done()
        return
    await callback.message.answer("Thank you. To start again click /start")
    await manager.done()


async def on_age_changed(callback: ChatEvent, select: ManagedWidgetAdapter,
                         manager: DialogManager,
                         item_id: str):
    ctx = manager.current_context()
    ctx.dialog_data["age"] = item_id
    await manager.dialog().next()


dialog = Dialog(
    Window(
        Const("Greetings! Please, introduce yourself:"),
        MessageInput(name_handler, content_types=[ContentType.TEXT]),
        # MessageInput(other_type_handler),
        state=DialogSG.greeting,
    ),
    Window(
        Format("{name}! How old are you?"),
        Select(
            Format("{item}"),
            items=["0-12", "12-18", "18-25", "25-40", "40+"],
            item_id_getter=lambda x: x,
            id="w_age",
            on_click=on_age_changed,
        ),
        state=DialogSG.age,
        getter=get_data,
        preview_data={"name": "Tishka17"}
    ),
    Window(
        Multi(
            Format("{name}! Thank you for your answers."),
            Const("Hope you are not smoking", when="can_smoke"),
            sep="\n\n",
        ),
        Row(
            Back(),
            SwitchTo(Const("Restart"), id="restart", state=DialogSG.greeting),
            Button(Const("Finish"), on_click=on_finish, id="finish"),
        ),
        getter=get_data,
        state=DialogSG.finish,
    )
)


async def start(message: Message, dialog_manager: DialogManager):
    # it is important to reset stack because user wants to restart everything
    await dialog_manager.start(DialogSG.greeting, mode=StartMode.RESET_STACK)


def new_registry(dp: Dispatcher):
    registry = DialogRegistry(dp)
    registry.register(dialog)
    return registry


async def main():
    # real main
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=API_TOKEN)

    storage = MemoryStorage()
    dp = Dispatcher(bot=bot, storage=storage)
    dp.register_message_handler(start, commands=["start"], state="*")
    registry = new_registry(dp)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
