from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
import time

accountID, token = exampleAuth()
instrument = "GBP_JPY"
params = {
    "count": 100,
    "granularity": "M1"
}
last_time = 0


def get_price(instrument, params):
    client = API(access_token=token)
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(r)

    # 最後から２番目のローソク足を取り出す
    data = response["candles"][-2]
    close_time = data["time"]
    open_price = data["mid"]["o"]
    close_price = data["mid"]["c"]
    return data, close_time, open_price, close_price


def print_price(close_time, open_price, close_price):
    print("時間： " + dateutil.parser.parse(close_time).strftime('%Y/%m/%d %H:%M')
          + " 始値： " + str(open_price)
          + " 終値： " + str(close_price))


while True:
    data, close_time, open_price, close_price = get_price(instrument, params)
    if close_time != last_time:
        last_time = close_time
        print_price(close_time, open_price, close_price)
    time.sleep(10)
