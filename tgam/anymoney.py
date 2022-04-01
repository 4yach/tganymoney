
from hmac import (
    new as hmac_new,
    HMAC)

from hashlib import sha512

from aiohttp import ClientSession


class AnyMoney:
    
    def __init__(self, api_key, endpoint="https://api.any.money/"):
        self._api_key = api_key
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
        _message = \
            _message.lower() + \
            utcs_now.lower()
        _message = _message.encode()
        
        # применяем алгоритм sha512 к запросу
        _hmac_o: HMAC = hmac_new(
            _api_key,
            _message,
            sha512)

        return _hmac_o.hexdigest()

    async def call_method(self, method: str, params: dict) -> dict:
        _result: dict = {}
        headers: dict = {}
        async with ClientSession(headers=headers) as _am_session:
            async with _am_session.post(url=self._endpoint, data=params) as _resp:
                _result = _resp.json()
        return _result

    async def invoice_create(
        self,
        merchant_id: str,
        currency: str,
        amount: str,
        email: str,
        lifetime: str):
        return await self.call_method(
            "invoice.create",
            {
                "externalid": merchant_id,
                "amount": amount,
                "in_curr": currency,
                "client_email": email,
                "lifetime": lifetime
            })
