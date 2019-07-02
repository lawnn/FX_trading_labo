from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
import time
import pandas as pd


term = 20
wait = 0


def get_price():
    client = API(access_token=token, environment="practice")
    instrument = "GBP_JPY"
    params = {
        "count": 50,
        "granularity": "H1"
    }
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    price = [{"close_time": client.request(r)["candles"][i]['time'],
              "open_price": round(float(client.request(r)["candles"][i]["mid"]['o']), 3),
              "high_price": round(float(client.request(r)["candles"][i]["mid"]['h']), 3),
              "low_price": round(float(client.request(r)["candles"][i]["mid"]['l']), 3),
              "close_price": round(float(client.request(r)["candles"][i]["mid"]['c']), 3)}
             for i in range(params['count'])]
    return price


def get_price_from_file():
    instrument = "GBP_JPY"
    params = {
        "count": 1,
        "granularity": "H1"
    }
    d = pd.read_csv('csv/' + instrument + '_' + params['granularity'] + '_' + '2017.1.1' + '.csv')
    price = [{"close_time": d.loc[i, 'time'],
              "open_price": round(d.loc[i, 'o'], 3),
              "high_price": round(d.loc[i, 'h'], 3),
              "low_price": round(d.loc[i, 'l'], 3),
              "close_price": round(d.loc[i, 'c'], 3)}
             for i in range(len(d))]
    return price


def print_price(data):
    print("時間： " + dateutil.parser.parse(data['close_time']).strftime('%Y/%m/%d %H:%M')
          + " 始値： " + str(data['open_price'])
          + " 終値： " + str(data['close_price']))


# ドンチャンブレイクを判定する関数
def donchian(data, last_data):
    highest = max(i["high_price"] for i in last_data)
    if data["high_price"] > highest:
        return {"side": "BUY", "price": highest}

    lowest = min(i["low_price"] for i in last_data)
    if data["low_price"] < lowest:
        return {"side": "SELL", "price": lowest}

    return {"side": None, "price": 0}


# ドンチャンブレイクを判定してエントリー注文を出す関数
def entry_signal(data, last_data, flag):
    signal = donchian(data, last_data)
    if signal["side"] == "BUY":
        print("過去{0}足の最高値{1}円を、直近の高値が{2}円でブレイクしました".format(term, signal["price"], data["high_price"]))
        print(str(data["close_price"]) + "円で買いの指値注文を出します")

        # ここに買い注文のコードを入れる

        flag["order"]["exist"] = True
        flag["order"]["side"] = "BUY"

    if signal["side"] == "SELL":
        print("過去{0}足の最安値{1}円を、直近の安値が{2}円でブレイクしました".format(term, signal["price"], data["low_price"]))
        print(str(data["close_price"]) + "円で売りの指値注文を出します")

        # ここに売り注文のコードを入れる

        flag["order"]["exist"] = True
        flag["order"]["side"] = "SELL"

    return flag


# サーバーに出した注文が約定したか確認する関数
def check_order(flag):
    # 注文状況を確認して通っていたら以下を実行
    # 一定時間で注文が通っていなければキャンセルする

    flag["order"]["exist"] = False
    flag["order"]["count"] = 0
    flag["position"]["exist"] = True
    flag["position"]["side"] = flag["order"]["side"]

    return flag


# 手仕舞いのシグナルが出たら決済の成行注文 + ドテン注文 を出す関数
def close_position(data, last_data, flag):
    flag["position"]["count"] += 1
    signal = donchian(data, last_data)

    if flag["position"]["side"] == "BUY":
        if signal["side"] == "SELL":
            print("過去{0}足の最安値{1}円を、直近の安値が{2}円でブレイクしました".format(term, signal["price"], data["low_price"]))
            print("成行注文を出してポジションを決済します")

            # 決済の成行注文コードを入れる

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            print("さらに" + str(data["close_price"]) + "円で売りの指値注文を入れてドテンします")

            # ここに売り注文のコードを入れる

            flag["order"]["exist"] = True
            flag["order"]["side"] = "SELL"

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            print("過去{0}足の最高値{1}円を、直近の高値が{2}円でブレイクしました".format(term, signal["price"], data["high_price"]))
            print("成行注文を出してポジションを決済します")

            # 決済の成行注文コードを入れる

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            print("さらに" + str(data["close_price"]) + "円で買いの指値注文を入れてドテンします")

            # ここに買い注文のコードを入れる

            flag["order"]["exist"] = True
            flag["order"]["side"] = "BUY"

    return flag


accountID, token = exampleAuth()
# client = API(access_token=token)
# instrument = "GBP_JPY"
# params = {
#     "count": 5000,
#     "granularity": "H1"
# }
# path = 'csv/' + instrument + '_' + params['granularity'] + '_' + '2017.1.1' + '.csv'
# r = instruments.InstrumentsCandles(instrument=instrument, params=params)



# ------------------------------
# ここからメイン処理
# ------------------------------

price = get_price_from_file()
last_data = []
#last_data = get_price_from_file(path, i)

flag = {
    "order": {
        "exist": False,
        "side": "",
        "count": 0
    },
    "position": {
        "exist": False,
        "side": "",
        "count": 0
    }
}

i = 0
while i < len(price):

    # ドンチャンの判定に使う過去ｎ足分の安値・高値データを準備する
    if len(last_data) < term:
        last_data.append(price[i])
        print_price(price[i])
        time.sleep(wait)
        i += 1
        continue

    data = price[i]
    print_price(data)

    if flag["order"]["exist"]:
        flag = check_order(flag)
    elif flag["position"]["exist"]:
        flag = close_position(data, last_data, flag)
    else:
        flag = entry_signal(data, last_data, flag)

    # 過去データをｎ個ピッタリに保つために先頭を削除
    del last_data[0]
    last_data.append(data)
    i += 1
    time.sleep(wait)
