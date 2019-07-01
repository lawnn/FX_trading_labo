from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
import time
import pandas as pd


def get_price(i):
    instrument = "GBP_JPY"
    params = {
        "count": 5000,
        "granularity": "H1"
    }
    accountID, token = exampleAuth()
    client = API(access_token=token)
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    data = client.request(r)

    return {"close_time": data["candles"][i]['time'],
            "open_price": round(float(data["candles"][i]["mid"]['o']), 3),
            "high_price": round(float(data["candles"][i]["mid"]['h']), 3),
            "low_price": round(float(data["candles"][i]["mid"]['l']), 3),
            "close_price": round(float(data["candles"][i]["mid"]['c']), 3)}


def get_price_from_file(path, i):
    data = pd.read_csv(path)

    return {"close_time": data.loc[i, 'time'],
            "open_price": round(data.loc[i, 'o'], 3),
            "high_price": round(data.loc[i, 'h'], 3),
            "low_price": round(data.loc[i, 'l'], 3),
            "close_price": round(data.loc[i, 'c'], 3)}


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


# 買いシグナルが点灯したら指値で買い注文する関数
def buy_signal(data, last_data, flag):
    if flag["buy_signal"] == 0 and check_candle(data):
        flag["buy_signal"] = 1
    elif flag["buy_signal"] == 1 and check_candle(data) and check_ascend(data, last_data):
        flag["buy_signal"] = 2
    elif flag["buy_signal"] == 2 and check_candle(data) and check_ascend(data, last_data):
        print("３本連続で陽線 なので" + str(data["close_price"]) + "で買い指値")
        # ここに買い注文のコードを入れる
        flag["buy_signal"] = 3
        flag["order"] = True
    else:
        flag["buy_signal"] = 0
    return flag


# 手仕舞いのシグナルが出たら決済の成行注文を出す関数
def close_position(data, last_data, flag):
    if data["close_price"] < last_data["close_price"]:
        print("前回の終値を下回ったので" + str(data["close_price"]) + "で決済")
        flag["position"] = False
    return flag


# サーバーに出した注文が約定したか確認する関数
def check_order(flag):
    # 注文状況を確認して通っていたら以下を実行
    # 一定時間で注文が通っていなければキャンセルする
    flag["order"] = False
    flag["position"] = True
    return flag


#path = 'csv/' + instrument + '_' + params['granularity'] + '_' + '2017.1.1' + '.csv'
last_data = get_price(-2)
#last_data = get_price_from_file(path, 0)
print_price(last_data)
flag = {"buy_signal": 0,
        "sell_signal": 0,
        "order": False,
        "position": False}
#i = 1

while True:
    if flag["order"]:
        flag = check_order(flag)

    data = get_price(-2)
    #data = get_price_from_file(path, i)
    if data["close_time"] != last_data["close_time"]:
        print_price(data)

        if flag["position"]:
            flag = close_position(data, last_data, flag)
        else:
            flag = buy_signal(data, last_data, flag)

        last_data["close_time"] = data["close_time"]
        last_data["open_price"] = data["open_price"]
        last_data["close_price"] = data["close_price"]
        #i += 1

    time.sleep(10)
