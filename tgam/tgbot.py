import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery, ContentType
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

API_TOKEN = ''

bot = Bot(token=API_TOKEN, parse_mode="HTML")

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# merchants id:key
merchants_keys = {
    '1111': '1',
    '2222': '2'
}

# merchants buttons title:id
merchants_btns = [
    ['name1', '1111'],
    ['name2', '2222']
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
Срок действия:\t{lifetime}</code>
'''

cancel_btn = types.InlineKeyboardButton('Завершить', callback_data='cancel')

regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')


class Form(StatesGroup):
    merchant = State()
    in_curr = State()
    amount = State()
    client_email = State()
    lifetime = State()


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await Form.merchant.set()

    inline_keyboard = types.InlineKeyboardMarkup()
    btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in merchants_btns)
    inline_keyboard.row(*btns)
    inline_keyboard.row(cancel_btn)

    await bot.send_message(
        chat_id=message.from_user.id,
        text='Выберете мерчант',
        reply_markup=inline_keyboard
    )


@dp.callback_query_handler(state='*', text='cancel')
async def cancel_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    await state.finish()
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Создание инвойса прекращено.'
    )


@dp.callback_query_handler(state=Form.merchant)
async def merchant_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Process of choice merchant
    """
    async with state.proxy() as data:
        data['merchant_id'] = callback_query.data
        data['message_id'] = callback_query.message.message_id  # сохраняем id сообщения с инлайн кнопками

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


@dp.callback_query_handler(state=Form.in_curr)
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
        text="Введите сумму оплаты",
        reply_markup=inline_keyboard
    )


@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.amount)
async def process_amount_invalid(message: types.Message, state: FSMContext):
    """
    If amount is invalid
    """
    async with state.proxy() as data:
        if data.get('amount_invalid_message') is None:
            invalid_message = await bot.send_message(
                chat_id=message.from_user.id,
                text='Сумма должна быть числом'
            )
            data['amount_invalid_message'] = invalid_message

    await message.delete()


@dp.message_handler(lambda message: message.text.isdigit(), state=Form.amount)
async def process_amount(message: types.Message, state: FSMContext):
    """
    Process of input amount
    """
    async with state.proxy() as data:
        data['amount'] = message.text
        message_id = data['message_id']
        if data.get('amount_invalid_message') is not None:
            await data['amount_invalid_message'].delete()

    await Form.next()
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.row(cancel_btn)

    await message.delete()

    await bot.edit_message_text(
        chat_id=message.from_user.id,
        message_id=message_id,
        text="Введите почту",
        reply_markup=inline_keyboard
    )


@dp.message_handler(state=Form.client_email)
async def process_client_email(message: types.Message, state: FSMContext):
    """
    Process of input client_email
    """
    # valid email
    if re.fullmatch(regex, message.text):
        async with state.proxy() as data:
            data['client_email'] = message.text
            message_id = data['message_id']
            if data.get('email_invalid_message') is not None:
                await data['email_invalid_message'].delete()

        await Form.next()

        inline_keyboard = types.InlineKeyboardMarkup()
        btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in lifetime_btns)
        inline_keyboard.row(*btns)
        inline_keyboard.row(cancel_btn)

        await message.delete()

        await bot.edit_message_text(
            chat_id=message.from_user.id,
            message_id=message_id,
            text="Выберете срок действия",
            reply_markup=inline_keyboard
        )
    # invalid email
    else:
        async with state.proxy() as data:
            if data.get('email_invalid_message') is None:
                invalid_message = await bot.send_message(
                    chat_id=message.from_user.id,
                    text='Неверный адрес почты'
                )
                data['email_invalid_message'] = invalid_message

        await message.delete()


@dp.callback_query_handler(state=Form.lifetime)
async def in_curr_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Process of choice lifetime
    """
    async with state.proxy() as data:
        data['lifetime'] = callback_query.data

        merchant_key = merchants_keys[data['merchant_id']]

        """
        Генерация ссылки
        """

        text = status_text.format(
            merchant=data['merchant_id'],
            in_curr=data['in_curr'],
            amount=data['amount'],
            email=data['client_email'],
            lifetime=data['lifetime']
        )
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=text
        )

    await state.finish()


@dp.message_handler(state='*', content_types=ContentType.ANY)
async def del_message(message: types.Message):
    await message.delete()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
