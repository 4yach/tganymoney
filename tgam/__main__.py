
from tgam import AnyMoneyDispatcher

from aiogram.utils import executor


if __name__ == "__main__":
    executor.start_polling(AnyMoneyDispatcher, skip_updates=True)
