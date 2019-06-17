from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import time

# APIで１分足を100件取得
instrument = "GBP_JPY"
params = {
    "count": 100,
    "granularity": "M1"
    }

accountID, token = exampleAuth()
client = API(access_token=token)
r = instruments.InstrumentsCandles(instrument=instrument, params=params)
response = client.request(r)
last_data = response["candles"][-2]
last_time = last_data["time"]
time.sleep(10)

while True:

    accountID, token = exampleAuth()
    client = API(access_token=token)
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(r)

    # 最後から２番目のローソク足を取り出す
    data = response["candles"][-2]

    # ローソク足から日時・始値・終値を取り出す
    close_time = data["time"]
    open_price = data["mid"]["o"]
    close_price = data["mid"]["c"]

    if close_time != last_time:
        print("時間： " + close_time
              + " 始値： " + str(open_price)
              + " 終値： " + str(close_price))
        last_time = close_time
    time.sleep(10)
