
from os import environ
from tgam import AnyMoney
from unittest import IsolatedAsyncioTestCase


class Test_AnyMoney(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self._any_money = AnyMoney(
            environ.get("TOKEN"),
            environ.get("MERCH"))

    async def test_call_method(self):
        data = await self._any_money.call_method(
            "balance", {
                "curr": "BTC"
            })
        self.assertTrue("error" not in data)

    async def test_create_invoice(self):
        # Test failed: specify payway, when preform one way (single) pay
        data = await self._any_money.invoice_create(
            "5450", "USDT", "1", "a.4yach@gmail.com", "1d")
        self.assertTrue("error" not in data)
