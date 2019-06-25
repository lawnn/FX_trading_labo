from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
import time
import pandas as pd


def get_price(response, i):
    data = response
    last_data = data["candles"][i]

    return {"close_time": last_data['time'],
            "open_price": float(last_data["mid"]['o']),
            "high_price": float(last_data["mid"]['h']),
            "low_price": float(last_data["mid"]['l']),
            "close_price": float(last_data["mid"]['c'])}


def get_price_from_file(path, i):
    last_data = pd.read_csv(path)

    return {"close_time": last_data.loc[i, 'time'],
            "open_price": round(last_data.loc[i, 'o'], 3),
            "high_price": round(last_data.loc[i, 'h'], 3),
            "low_price": round(last_data.loc[i, 'l'], 3),
            "close_price": round(last_data.loc[i, 'c'], 3)}


def print_price(data):
    print("時間： " + dateutil.parser.parse(data['close_time']).strftime('%Y/%m/%d %H:%M')
          + " 始値： " + str(data['open_price'])
          + " 終値： " + str(data['close_price']))


def check_candle(data):
    global increase_rate
    try:
        realbody_rate = abs(float(data["close_price"]) - float(data["open_price"])) / (float(data["high_price"]) - float(data["low_price"]))
        increase_rate = float(data["close_price"]) / float(data["open_price"]) - 1
    except ZeroDivisionError:
        print("ZeroDivisionError!!")


    if float(data["close_price"]) < float(data["open_price"]):
        return False
    elif increase_rate < 0.0005:
        return False
    elif realbody_rate < 0.5:
        return False
    else:
        return True


def check_ascend(data, last_data):
    if float(data["open_price"]) > float(last_data["open_price"]) \
            and float(data["close_price"]) > float(last_data["close_price"]):
        return True
    else:
        return False


accountID, token = exampleAuth()
client = API(access_token=token)
instrument = "GBP_JPY"
params = {
    "count": 5000,
    "granularity": "H1"
}
path = 'csv/' + instrument + '_' + params['granularity'] + '_' + '2017.1.1' + '.csv'
r = instruments.InstrumentsCandles(instrument=instrument, params=params)
response = client.request(r)
i = 0
last_data = get_price(response, i)
print_price(last_data)
flag = 0

while i < 5000:
    data = get_price_from_file(path, i)
    if data["close_time"] != last_data["close_time"]:
        print_price(data)
        if flag == 0 and check_candle(data):
            flag = 1
        elif flag == 1 and check_candle(data) and check_ascend(data, last_data):
            print("２本連続で陽線")
            flag = 2
        elif flag == 2 and check_candle(data) and check_ascend(data, last_data):
            print("３本連続で陽線 なので 買い！")
            flag = 3
        else:
            flag = 0
        last_data["close_time"] = data["close_time"]
        last_data["open_price"] = data["open_price"]
        last_data["close_price"] = data["close_price"]
    i += 1
    time.sleep(0)
