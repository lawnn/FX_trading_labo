from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import time

while True:

    accountID, token = exampleAuth()
    client = API(access_token=token)

    # APIで１分足を100件取得
    instrument = "GBP_JPY"
    params = {
        "count": 100,
        "granularity": "M1"
    }
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(r)

    # 最後から２番目のローソク足を取り出す
    data = response["candles"][-2]

    # ローソク足から日時・始値・終値を取り出す
    close_time = data["time"]
    open_price = data["mid"]["o"]
    close_price = data["mid"]["c"]

    print("時間： " + close_time
          + " 始値： " + str(open_price)
          + " 終値： " + str(close_price))

    time.sleep(10)
