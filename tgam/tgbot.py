import re
import logging

from configparser import ConfigParser

from tgam.anymoney import AnyMoney

from aiogram import (
    Bot,
    Dispatcher,
    types)
from aiogram.types import CallbackQuery, ContentType
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# конфигурируем лог
logging.basicConfig(
    level=logging.INFO)

# открываем конфиг файл
_cfg = ConfigParser()

if "config.cfg" not in _cfg.read("config.cfg"):
    raise Exception("Config is missing, create config.cfg in 'tganymoney'")

_app = _cfg["App"]

# проверяем наличие токена в конфиге, если такого нет выводим ошибку
if "TG_TOKEN" in _app:
    bot = Bot(
        token=_app["TG_TOKEN"],
        parse_mode="HTML")
else:
    raise Exception("Bot token is missing in config file")

storage = MemoryStorage()

AnyMoneyDispatcher = Dispatcher(
    bot,
    storage=storage)

merchant_apis = {
    _app['AM_MERCH0']: _app["AM_API0"],
    _app['AM_MERCH1']: _app["AM_API1"]
}

# merchants buttons title:data
merchants_btns = [
    [_app['AM_NAME0'], _app["AM_MERCH0"]],
    [_app['AM_NAME1'], _app["AM_MERCH1"]]
]

# in_curr buttons title:data
in_curr_btns = [
    ['USDT', 'USDT']
]

# lifetime buttons title:data
lifetime_btns = [
    ['3 часа', '3h'],
    ['12 часов', '12h'],
    ['1 день', '1d']
]

status_text = '''
<code>Мерчант:\t{merchant}
Валюта:\t{in_curr}
Сумма:\t{amount}
Почта:\t{email}
Срок действия:\t{lifetime}</code>,
<b><a href="{link}">Ссылка на оплату</a></b>
'''

link_text = '''
<b><a href="{link}">Ссылка на оплату</a></b>
'''

cancel_btn = types.InlineKeyboardButton('Завершить', callback_data='cancel')

regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')


def _is_float(string: str) -> bool:
    string = string.replace(",", ".")
    try:
        float(string)
    except Exception:
        return False
    return True


class Form(StatesGroup):
    merchant = State()
    in_curr = State()
    amount = State()
    client_email = State()
    lifetime = State()


@AnyMoneyDispatcher.message_handler(lambda message: message.text == 'start',  state='*')
@AnyMoneyDispatcher.message_handler(state='*', commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):

    async with state.proxy() as data:
        current_state = await state.get_state()
        if current_state is not None:
            if "invalid_message" in data:
                await data["invalid_message"].delete()
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=data['message_id']
            )
            await state.finish()

    await Form.merchant.set()
    await message.delete()

    inline_keyboard = types.InlineKeyboardMarkup()
    btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in merchants_btns)
    inline_keyboard.row(*btns)
    inline_keyboard.row(cancel_btn)

    inline_message = await bot.send_message(
        chat_id=message.from_user.id,
        text='Выберете мерчант',
        reply_markup=inline_keyboard
    )
    async with state.proxy() as data:
        data['message_id'] = inline_message.message_id  # сохраняем id сообщения с инлайн кнопками


@AnyMoneyDispatcher.callback_query_handler(state='*', text='cancel')
@AnyMoneyDispatcher.callback_query_handler(text='cancel')
async def cancel_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Allow user to cancel any action
    """

    # удаляем сообщение об ошибке и меню
    async with state.proxy() as data:
        if "invalid_message" in data:
            await data["invalid_message"].delete()

    await callback_query.message.delete()

    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    await state.finish()
    await bot.answer_callback_query(
        callback_query_id=callback_query.id,
        text='Создание инвойса прекращено.'
    )


@AnyMoneyDispatcher.callback_query_handler(state=Form.merchant)
async def merchant_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Process of choice merchant
    """
    async with state.proxy() as data:
        data['merchant_id'] = callback_query.data

    await Form.next()

    inline_keyboard = types.InlineKeyboardMarkup()
    btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in in_curr_btns)
    inline_keyboard.row(*btns)
    inline_keyboard.row(cancel_btn)

    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text="Выберете валюту",
        reply_markup=inline_keyboard
    )


@AnyMoneyDispatcher.callback_query_handler(state=Form.in_curr)
async def in_curr_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Process of choice in_curr
    """
    async with state.proxy() as data:
        data['in_curr'] = callback_query.data
    await Form.next()

    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.row(cancel_btn)

    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text="Введите сумму оплаты (Например: 3990 или 3990,45)",
        reply_markup=inline_keyboard
    )


@AnyMoneyDispatcher.message_handler(lambda message: not _is_float(message.text), state=Form.amount)
async def process_amount_invalid(message: types.Message, state: FSMContext):
    """
    If amount is invalid
    """
    async with state.proxy() as data:
        if data.get('invalid_message') is None:
            invalid_message = await bot.send_message(
                chat_id=message.from_user.id,
                text='Сумма должна быть числом'
            )
            data['invalid_message'] = invalid_message

    await message.delete()


@AnyMoneyDispatcher.message_handler(lambda message: _is_float(message.text), state=Form.amount)
async def process_amount(message: types.Message, state: FSMContext):
    """
    Process of input amount
    """
    async with state.proxy() as data:
        data['amount'] = message.text
        message_id = data['message_id']
        if data.get('invalid_message') is not None:
            await data['invalid_message'].delete()
            del data['invalid_message']

    await Form.next()
    await message.delete()

    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.row(cancel_btn)

    await bot.edit_message_text(
        chat_id=message.from_user.id,
        message_id=message_id,
        text="Введите почту",
        reply_markup=inline_keyboard
    )


@AnyMoneyDispatcher.message_handler(state=Form.client_email)
async def process_client_email(message: types.Message, state: FSMContext):
    """
    Process of input client_email
    """
    # valid email
    if re.fullmatch(regex, message.text):
        async with state.proxy() as data:
            data['client_email'] = message.text
            message_id = data['message_id']
            if data.get('invalid_message') is not None:
                await data['invalid_message'].delete()
                del data['invalid_message']

        await Form.next()
        await message.delete()

        inline_keyboard = types.InlineKeyboardMarkup()
        btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in lifetime_btns)
        inline_keyboard.row(*btns)
        inline_keyboard.row(cancel_btn)

        await bot.edit_message_text(
            chat_id=message.from_user.id,
            message_id=message_id,
            text="Выберете срок действия",
            reply_markup=inline_keyboard
        )
    # invalid email
    else:
        async with state.proxy() as data:
            if data.get('invalid_message') is None:
                invalid_message = await bot.send_message(
                    chat_id=message.from_user.id,
                    text='Неверный адрес почты'
                )
                data['invalid_message'] = invalid_message

        await message.delete()


@AnyMoneyDispatcher.callback_query_handler(state=Form.lifetime)
async def in_curr_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Process of choice lifetime
    """
    async with state.proxy() as data:
        data['lifetime'] = callback_query.data

        # генерация ссылки

        _merch_id = data["merchant_id"]
        _merch_api = merchant_apis[_merch_id]
        _in_curr = data["in_curr"]
        _amount = data["amount"]
        _email = data["client_email"]
        _lifetime = data["lifetime"]

        # делаем запрос
        anymoney = AnyMoney(_merch_api, _merch_id)
        _am_data = await anymoney.invoice_create(
            _merch_id,
            _in_curr,
            _amount,
            _email,
            _lifetime)

        # пишем ошибку в лог, если нет paylink
        if "result" not in _am_data:
            raise Exception("'result' is missing in server responce, got: %s" % _am_data)
        else:
            await bot.edit_message_text(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                disable_web_page_preview=True,
                text=link_text.format(
                    merchant=_merch_id,
                    in_curr=_in_curr,
                    amount=_amount,
                    email=_email,
                    lifetime=_lifetime,
                    link=_am_data["result"]["paylink"]
                )
            )

    await state.finish()


@AnyMoneyDispatcher.message_handler(state='*', content_types=ContentType.ANY)
async def del_message(message: types.Message):
    await message.delete()


__all__ = (
    "AnyMoneyDispatcher",
)
