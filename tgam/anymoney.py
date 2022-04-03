
from uuid import uuid1

from time import time

from hmac import (
    new as hmac_new,
    HMAC)

from hashlib import sha512

from aiohttp import ClientSession


class AnyMoney:

    """
    Класс с полезными методами для работы с API сервиса Any.Money
    """
    
    def __init__(self, api_key, merchant, endpoint="https://api.any.money/"):
        self._api_key = api_key
        self._merchant = merchant
        self._endpoint = endpoint

    def _sign(self, data: dict, utcs_now: str) -> str:

        # закодируем ключ API сразу
        _api_key = self._api_key.encode()

        # словарь должен быть отсортирован
        if data:
            data = sorted(data.items())

        # формируем строку из значений data без вложенный объектов и null
        _message = ''
        for _, val in data:
            # избавляемся от вложенностей и null
            if not isinstance(val, (dict, list, type(None))):
                _message += str(val)
        _message = _message.lower() + utcs_now
        _message = _message.encode()
        
        # применяем алгоритм sha512 к запросу
        _hmac_o: HMAC = hmac_new(
            _api_key,
            _message,
            sha512)

        return _hmac_o.hexdigest()

    def _get_utcms(self) -> str:
        return str(int(time() * 1000))

    async def call_method(self, method: str, params: dict) -> dict:
        """
        Вызываем RPC методы сервиса Any.Money

        :param str method: имя метода, который нужно вызвать (Например: invoice.create)
        :param dict params: словарь с параметрами, без вложенностей, без массивов и None
        :return dict: JSON ответ
        """
        _result: dict = {}

        # формируем заголовки
        _utc: str = self._get_utcms()
        _headers = {
            "x-merchant": self._merchant,
            "x-signature": self._sign(params, _utc),
            "x-utc-now-ms": _utc
        }

        # формируем данные
        _data = {
            "method": method,
            "params": params,
            "jsonrpc": "2.0",
            "id": "1"
        }

        async with ClientSession() as cs:
            async with cs.post(url=self._endpoint, json=_data, headers=_headers) as _resp:
                _result = await _resp.json()
        return _result

    async def invoice_create(
        self,
        merchant_id: str,
        currency: str,
        amount: str,
        email: str,
        lifetime: str) -> dict:
        """
        Создать инвойс (ордер) для оплаты в определенной валюте и
        до определенного срока.
        :param str merchant_id: уникальный номер мерчанта
        :param str currency: валюта, в которой будет произведена оплата
        :param str amount: счет, например 3002,10
        :params str email: почта клиента, куда придет оповещение об операции
        :param str lifetime: время активности ордера
        :return dict: ответ сервера
        """
        return await self.call_method(
            "invoice.create",
            {
                "externalid": str(uuid1()),
                "amount": amount,
                "in_curr": currency,
                "client_email": email,
                "lifetime": lifetime,
                # FIXME: точно неизвестно, односторонний платеж (без возврата) или нет
                "is_multipay": True
            })
