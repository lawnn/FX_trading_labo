from auth import exampleAuth
import requests
from logging import getLogger, StreamHandler, FileHandler, INFO
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
from oandapyV20.exceptions import V20Error
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.positions as positions
from datetime import datetime
import time
import numpy as np
from pprint import pprint

accountID, token, line_token = exampleAuth()
currency = "USD_JPY"
gran = "M15"


# OANDA APIに成り行き注文する関数
def oanda_market(side, lot):
    # lotが買いか売りを判定する
    if side == "BUY":
        units = lot
    if side == "SELL":
        units = -1 * lot

    # 注文内容
    order = {'order': {
        "instrument": currency,
        "units": units,
        "type": "MARKET",
        "positionFill": "DEFAULT"
    }}

    # API取得
    api = API(access_token=token)
    order = orders.OrderCreate(accountID, data=order)
    position = positions.OpenPositions(accountID=accountID)

    while True:
        time.sleep(30)

        # 執行状況を確認
        if units > 0:
            while True:
                try:
                    # 注文実行
                    api.request(order)                  # API元にrequestを送る(order)
                    position = api.request(position)    # API元にrequestを送る(position)
                    average_price = position['positions'][0]['long']['averagePrice']
                    pprint(order)
                    pprint("注文がすべて約定するのを待っています")
                    time.sleep(20)
                    pprint("\nすべての成行注文が執行されました\n執行価格は平均 {}円です".format(average_price))
                    return float(average_price)

                except V20Error as e:
                    pprint("\nOANDAのAPIで問題発生\n" + str(e))
                    break

        elif units < 0:
            while True:
                try:
                    # 注文実行
                    api.request(order)                  # API元にrequestを送る(order)
                    position = api.request(position)    # API元にrequestを送る(position)
                    average_price = position['positions'][0]['short']['averagePrice']
                    pprint(order)
                    pprint("注文がすべて約定するのを待っています")
                    time.sleep(20)
                    pprint("\nすべての成行注文が執行されました\n執行価格は平均 {}円です".format(average_price))
                    return float(average_price)

                except V20Error as e:
                    pprint("\nOANDAのAPIで問題発生\n" + str(e))
                    break


# 注文決済する関数
def oanda_close_positions(side):
    # API取得
    api = API(access_token=token)

    # 注文内容
    if side == "BUY":
        order_data = {"shortUnits": "ALL"}
    if side == "SELL":
        order_data = {"longUnits": "ALL"}

    while True:
        # 注文実行
        try:
            r = positions.PositionClose(accountID, instrument=currency, data=order_data)
            api.request(r)
            pprint("\nすべての建玉を決済しました\n決済価格は平均 {}円です".format(str(data["forming"]["close_price"])))
            return order_data

        except V20Error as e:
            pprint("OANDAのAPIで問題発生" + str(e))
            break


# 口座残高を取得する関数
def oanda_collateral():
    api = API(access_token=token)
    r = accounts.AccountSummary(accountID)

    while True:
        try:

            rv = api.request(r)
            pprint(rv)
            balance = rv['account']['balance']
            spendable_collateral = float(rv['account']['withdrawalLimit'])
            pprint('現在の口座残高は{}円です。'.format(round(int(float(balance)))))
            pprint("新規注文に利用可能な証拠金の額は{}円です".format(round(int(spendable_collateral))))
            return int(spendable_collateral)

        except V20Error as e:
            pprint("OANDAのAPIでの口座残高取得に失敗しました ： " + str(e))
            break


# OANDAのチャート価格をAPIで取得する関数（リアルタイム用）
def get_realtime_price():
    params = {
        "count": 100,
        "granularity": gran
    }
    while True:
        try:
            api = API(access_token=token, headers={"Accept-Datetime-Format": "Unix"})
            r = instruments.InstrumentsCandles(instrument=currency, params=params)
            rv = api.request(r)
            return {
                "settled": {
                    "close_time": rv["candles"][-2]['time'],
                    "open_price": round(float(rv["candles"][-2]["mid"]['o']), 3),
                    "high_price": round(float(rv["candles"][-2]["mid"]['h']), 3),
                    "low_price": round(float(rv["candles"][-2]["mid"]['l']), 3),
                    "close_price": round(float(rv["candles"][-2]["mid"]['c']), 3)
                },
                "forming": {"close_time": rv["candles"][-1]['time'],
                            "open_price": round(float(rv["candles"][-1]["mid"]['o']), 3),
                            "high_price": round(float(rv["candles"][-1]["mid"]['h']), 3),
                            "low_price": round(float(rv["candles"][-1]["mid"]['l']), 3),
                            "close_price": round(float(rv["candles"][-1]["mid"]['c']), 3)
                            }
            }

        except requests.exceptions.RequestException as e:
            pprint("OANDAの価格取得でエラー発生 : " + str(e))
            pprint("{}秒待機してやり直します".format(10))
            time.sleep(10)


def check_position():
    api = API(access_token=token)
    position = positions.OpenPositions(accountID=accountID)
    position = api.request(position)    # API元にrequestを送る(position)
    pprint(position)


data = get_realtime_price()
check_position()

# oanda_collateral()



# example
# {'lastTransactionID': '38',
#  'orderCreateTransaction': {'accountID': '101-009-11452891-001',
#                             'batchID': '37',
#                             'id': '37',
#                             'instrument': 'USD_JPY',
#                             'positionFill': 'DEFAULT',
#                             'reason': 'CLIENT_ORDER',
#                             'requestID': '42595366173843970',
#                             'time': '2019-08-12T06:41:27.635685586Z',
#                             'timeInForce': 'FOK',
#                             'type': 'MARKET_ORDER',
#                             'units': '-2',
#                             'userID': 11452891},
#  'orderFillTransaction': {'accountBalance': '2999986.0740',
#                           'accountID': '101-009-11452891-001',
#                           'batchID': '37',
#                           'commission': '0.0000',
#                           'financing': '0.0000',
#                           'fullPrice': {'asks': [{'liquidity': '250000',
#                                                   'price': '105.425'}],
#                                         'bids': [{'liquidity': '250000',
#                                                   'price': '105.421'}],
#                                         'closeoutAsk': '105.444',
#                                         'closeoutBid': '105.402',
#                                         'timestamp': '2019-08-12T06:41:11.214530239Z'},
#                           'fullVWAP': '105.421',
#                           'gainQuoteHomeConversionFactor': '1',
#                           'guaranteedExecutionFee': '0.0000',
#                           'halfSpreadCost': '0.0040',
#                           'id': '38',
#                           'instrument': 'USD_JPY',
#                           'lossQuoteHomeConversionFactor': '1',
#                           'orderID': '37',
#                           'pl': '0.0000',
#                           'price': '105.421',
#                           'reason': 'MARKET_ORDER',
#                           'requestID': '42595366173843970',
#                           'requestedUnits': '-2',
#                           'time': '2019-08-12T06:41:27.635685586Z',
#                           'tradeOpened': {'guaranteedExecutionFee': '0.0000',
#                                           'halfSpreadCost': '0.0040',
#                                           'initialMarginRequired': '8.4338',
#                                           'price': '105.421',
#                                           'tradeID': '38',
#                                           'units': '-2'},
#                           'type': 'ORDER_FILL',
#                           'units': '-2',
#                           'userID': 11452891},
#  'relatedTransactionIDs': ['37', '38']}

