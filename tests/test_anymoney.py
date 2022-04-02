
from os import environ
from tgam import AnyMoney
from unittest import IsolatedAsyncioTestCase
from configparser import ConfigParser


_config = ConfigParser()


class Test_AnyMoney(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        _config.read("config.cfg")

        _test = _config["Tests"]

        if _test != None:
            self._any_money = AnyMoney(
                _test.get("TOKEN"),
                _test.get("MERCH"))  # renamed env. variables, to not shadow real variables
        else:
            raise Exception("'Tests' section is missing")

    async def test_call_method(self):
        data = await self._any_money.call_method(
            "balance", {
                "curr": "BTC"
            })
        self.assertTrue("error" not in data)

    async def test_create_invoice(self):
        data = await self._any_money.invoice_create(
            "5450", "USDT", "1", "a.4yach@gmail.com", "1d")
        self.assertTrue("error" not in data)
