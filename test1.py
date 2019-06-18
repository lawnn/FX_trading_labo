from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
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
# 前回の時間を last_time に入れる
last_data = response["candles"][-2]
last_time = dateutil.parser.parse(last_data["time"]).strftime('%Y/%m/%d %H:%M')
time.sleep(10)

while True:

    accountID, token = exampleAuth()
    client = API(access_token=token)
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(r)

    # 最後から２番目のローソク足を取り出す
    data = response["candles"][-2]

    # ローソク足から日時・始値・終値を取り出す
    # 今回の時間を close_time に入れる
    close_time = dateutil.parser.parse(data["time"]).strftime('%Y/%m/%d %H:%M')
    open_price = data["mid"]["o"]
    close_price = data["mid"]["c"]
    # 前回の時間（last_time）と今回の時間（close_time）が違う場合のみprintする
    if close_time != last_time:
        print("時間： " + close_time
              + " 始値： " + str(open_price)
              + " 終値： " + str(close_price))
        # 前回の時間（last_time）を今回の時間（close_time）で上書きする
        last_time = close_time
    time.sleep(10)
