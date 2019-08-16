from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
from datetime import datetime
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# -------------設定項目------------------------

wait = 0                   # ループの待機時間
buy_term = 10              # 買いエントリーのブレイク期間の設定
sell_term = 10             # 売りエントリーのブレイク期間の設定

judge_price = {
  "BUY": "high_price",    # ブレイク判断　高値（high_price)か終値（close_price）を使用
  "SELL": "low_price"    # ブレイク判断　安値 (low_price)か終値（close_price）を使用
}

TEST_MODE_LOT = "adjustable"  # fixed なら常に1通貨固定 / adjustable なら可変ロット
volatility_term = 4       # 平均ボラティリティの計算に使う期間
stop_range = 11             # 何レンジ幅に損切（ストップ）を置くか
trade_risk = 0.05          # 1トレードあたり口座の何％まで損失を許容するか
leverage = 25               # レバレッジ倍率の設定
start_funds = 500000       # シミュレーション時の初期資金

entry_times = 4            # 何回に分けて追加ポジションを取るか
entry_range = 0.5            # 何レンジごとに追加ポジションを取るか

stop_config = "TRAILING"         # ON / OFF / TRAILING の３つが設定可
stop_AF = 0.01             # 加速係数
stop_AF_add = 0.01         # 加速係数を増やす度合
stop_AF_max = 0.1          # 加速係数の上限

filter_VER = "OFF"           # フィルター設定／OFFで無効
MA_term = 30              # トレンドフィルターに使う移動平均線の期間
Short_EMA_term = 7
Long_EMA_term = Short_EMA_term * 2

accountID, token, line_token = exampleAuth()
instrument = "USD_JPY"
params = {
    "count": 5000,
    "granularity": "M15"
}
if params.get("granularity") == "M1":
    chart_sec = 1800  # 1分足を使用
elif params.get("granularity") == "M5":
    chart_sec = 1800  # 5分足を使用
elif params.get("granularity") == "M15":
    chart_sec = 900  # 15分足を使用
elif params.get("granularity") == "M30":
    chart_sec = 1800  # 30分足を使用
elif params.get("granularity") == "H1":
    chart_sec = 3600  # 1時間足を使用
elif params.get("granularity") == "H2":
    chart_sec = 7200  # 2時間足を使用

flag = {
    "position": {
        "exist": False,
        "side": "",
        "price": 0,
        "stop": 0,
        "stop-AF": stop_AF,
        "stop-EP": 0,
        "ATR": 0,
        "lot": 0,
        "count": 0
    },
    "add-position": {
        "count": 0,
        "first-entry-price": 0,
        "last-entry-price": 0,
        "unit-range": 0,
        "unit-size": 0,
        "stop": 0
    },
    "records": {
        "date": [],
        "profit": [],
        "return": [],
        "side": [],
        "stop-count": [],
        "funds": start_funds,
        "holding-periods": [],
        "log": []
    }
}


# -------------売買ロジックの部分の関数--------------

# ドンチャンブレイクを判定する関数
def donchian(data, last_data):
    highest = max(i["high_price"] for i in last_data[(-1 * buy_term):])
    if data[judge_price["BUY"]] > highest:
        return {"side": "BUY", "price": highest}

    lowest = min(i["low_price"] for i in last_data[(-1 * sell_term):])
    if data[judge_price["SELL"]] < lowest:
        return {"side": "SELL", "price": lowest}

    return {"side": None, "price": 0}


# エントリー注文を出す関数
def entry_signal(data, last_data, flag):
    if flag["position"]["exist"] == True:
        return flag

    signal = donchian(data, last_data)
    if signal["side"] == "BUY":
        flag["records"]["log"].append(
            "過去{0}足の最高値{1}円を、直近の価格が{2}円でブレイクしました\n".format(buy_term, signal["price"], data[judge_price["BUY"]]))
        # フィルター条件を確認
        if filter(signal) == False:
            flag["records"]["log"].append("フィルターのエントリー条件を満たさなかったため、エントリーしません\n")
            return flag

        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot > 0.01:
            flag["records"]["log"].append("{0}円で{1}通貨の買い注文を出します\n".format(data["close_price"], lot))

            # ここに買い注文のコードを入れる

            flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] - stop))
            flag["position"]["lot"], flag["position"]["stop"] = lot, stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "BUY"
            flag["position"]["price"] = data["close_price"]
        else:
            flag["records"]["log"].append("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))

    if signal["side"] == "SELL":
        flag["records"]["log"].append(
            "過去{0}足の最安値{1}円を、直近の価格が{2}円でブレイクしました\n".format(sell_term, signal["price"], data[judge_price["SELL"]]))

        # フィルター条件を確認
        if filter(signal) == False:
            flag["records"]["log"].append("フィルターのエントリー条件を満たさなかったため、エントリーしません\n")
            return flag

        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot > 0.01:
            flag["records"]["log"].append("{0}円で{1}通貨の売り注文を出します\n".format(data["close_price"], lot))

            # ここに売り注文のコードを入れる

            flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] + stop))
            flag["position"]["lot"], flag["position"]["stop"] = lot, stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "SELL"
            flag["position"]["price"] = data["close_price"]
        else:
            flag["records"]["log"].append("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))

    return flag


# 損切ラインにかかったら成行注文で決済する関数
def stop_position(data, flag):
    # トレイリングストップを実行
    if stop_config == "TRAILING":
        flag = trail_stop(data, flag)

    if flag["position"]["side"] == "BUY":
        stop_price = flag["position"]["price"] - flag["position"]["stop"]
        if data["low_price"] < stop_price:
            flag["records"]["log"].append("{0}円の損切ラインに引っかかりました。\n".format(stop_price))
            stop_price = round(stop_price - 4 * calculate_volatility(last_data) / (chart_sec / 60), 4)
            flag["records"]["log"].append(str(stop_price) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data, stop_price, "STOP")
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

    if flag["position"]["side"] == "SELL":
        stop_price = flag["position"]["price"] + flag["position"]["stop"]
        if data["high_price"] > stop_price:
            flag["records"]["log"].append("{0}円の損切ラインに引っかかりました。\n".format(stop_price))
            stop_price = round(stop_price + 4 * calculate_volatility(last_data) / (chart_sec / 60), 4)
            flag["records"]["log"].append(str(stop_price) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data, stop_price, "STOP")
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

    return flag


# 手仕舞いのシグナルが出たら決済の成行注文 + ドテン注文 を出す関数
def close_position(data, last_data, flag):
    if flag["position"]["exist"] == False:
        return flag

    flag["position"]["count"] += 1
    signal = donchian(data, last_data)

    if flag["position"]["side"] == "BUY":
        if signal["side"] == "SELL":
            flag["records"]["log"].append(
                "過去{0}足の最安値{1}円を、直近の価格が{2}円でブレイクしました\n".format(sell_term, signal["price"], data[judge_price["SELL"]]))
            flag["records"]["log"].append(str(data["close_price"]) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data, data["close_price"])
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            # ドテン注文の箇所
            # フィルター条件を確認
            if filter(signal) == False:
                flag["records"]["log"].append("フィルターのエントリー条件を満たさなかったため、ドテンエントリーはしません\n")
                return flag

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot >= 0.01:
                flag["records"]["log"].append("\n{0}円で{1}通貨の売りの注文を入れてドテンします\n".format(data["close_price"], lot))

                # ここに売り注文のコードを入れる

                flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] + stop))
                flag["position"]["lot"], flag["position"]["stop"] = lot, stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "SELL"
                flag["position"]["price"] = data["close_price"]

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            flag["records"]["log"].append(
                "過去{0}足の最高値{1}円を、直近の価格が{2}円でブレイクしました\n".format(buy_term, signal["price"], data[judge_price["BUY"]]))
            flag["records"]["log"].append(str(data["close_price"]) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data, data["close_price"])
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            # ドテン注文の箇所
            # フィルター条件を確認
            if filter(signal) == False:
                flag["records"]["log"].append("フィルターのエントリー条件を満たさなかったため、ドテンエントリーはしません\n")
                return flag

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot > 0.01:
                flag["records"]["log"].append("\n{0}円で{1}通貨の買いの注文を入れてドテンします\n".format(data["close_price"], lot))

                # ここに買い注文のコードを入れる

                flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] - stop))
                flag["position"]["lot"], flag["position"]["stop"] = lot, stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "BUY"
                flag["position"]["price"] = data["close_price"]

    return flag


# -------------トレンドフィルターの関数--------------

# トレンドフィルターの関数
def filter(signal):
    if filter_VER == "OFF":
        return True

    if filter_VER == "A":
        if len(last_data) < MA_term:
            return True
        if data.get("close_price") > calculate_MA(MA_term) and signal["side"] == "BUY":
            return True
        if data.get("close_price") < calculate_MA(MA_term) and signal["side"] == "SELL":
            return True

    if filter_VER == "B":
        if len(last_data) < MA_term:
            return True
        if calculate_MA(MA_term) > calculate_MA(MA_term, -1) and signal["side"] == "BUY":
            return True
        if calculate_MA(MA_term) < calculate_MA(MA_term, -1) and signal["side"] == "SELL":
            return True

    if filter_VER == "C":
        if len(last_data) < (Long_EMA_term * 2):
            return True
        if calculate_EMA(Long_EMA_term) < calculate_EMA(Short_EMA_term) and signal["side"] == "BUY":
            return True
        if calculate_EMA(Long_EMA_term) > calculate_EMA(Short_EMA_term) and signal["side"] == "SELL":
            return True
    return False


# 単純移動平均を計算する関数
def calculate_MA(value, before=None):
    if before is None:
        MA = sum(i["close_price"] for i in last_data[-1 * value:]) / value
    else:
        MA = sum(i["close_price"] for i in last_data[-1 * value + before: before]) / value
    return round(MA, 4)


# 指数移動平均を計算する関数
def calculate_EMA(value, before=None):
    if before is not None:
        MA = sum(i["close_price"] for i in last_data[-2 * value + before: -1 * value + before]) / value
        EMA = (last_data[-1 * value + before]["close_price"] * 2 / (value + 1)) + (MA * (value - 1) / (value + 1))
        for i in range(value - 1):
            EMA = (last_data[-1 * value + before + 1 + i]["close_price"] * 2 / (value + 1)) + (
                        EMA * (value - 1) / (value + 1))
    else:
        MA = sum(i["close_price"] for i in last_data[-2 * value: -1 * value]) / value
        EMA = (last_data[-1 * value]["close_price"] * 2 / (value + 1)) + (MA * (value - 1) / (value + 1))
        for i in range(value - 1):
            EMA = (last_data[-1 * value + 1 + i]["close_price"] * 2 / (value + 1)) + (EMA * (value - 1) / (value + 1))
    return round(EMA, 4)


# -------------資金管理の関数--------------

# 注文ロットを計算する関数
def calculate_lot(last_data, data, flag):
    # 固定ロットでのテスト時
    if TEST_MODE_LOT == "fixed":
        flag["records"]["log"].append("固定ロット(1枚)でテスト中のため、10000通貨を注文します\n")
        lot = 10000
        volatility = calculate_volatility(last_data)
        stop = stop_range * volatility
        flag["position"]["ATR"] = round(volatility, 4)
        return lot, stop, flag

    # 口座残高を取得する
    balance = flag["records"]["funds"]

    # 最初のエントリーの場合
    if flag["add-position"]["count"] == 0:

        # １回の注文単位（ロット数）と、追加ポジの基準レンジを計算する
        volatility = round(calculate_volatility(last_data), 4)
        stop = round(stop_range * volatility, 4)
        calc_lot = int(round(np.floor(balance * trade_risk / stop * 100) / 100, -3))

        flag["add-position"]["unit-size"] = int(np.floor(calc_lot / entry_times * 100) / 100)
        flag["add-position"]["unit-range"] = round(volatility * entry_range, 4)
        flag["add-position"]["stop"] = stop
        flag["position"]["ATR"] = volatility

        flag["records"]["log"].append("\n現在のアカウント残高は{}円です\n".format(balance))
        flag["records"]["log"].append("許容リスクから購入できる枚数は最大{}通貨までです\n".format(calc_lot))
        flag["records"]["log"].append("{0}回に分けて{1}通貨ずつ注文します\n".format(entry_times, flag["add-position"]["unit-size"]))

    # ２回目以降のエントリーの場合
    else:
        balance = round(balance - flag["position"]["price"] * flag["position"]["lot"] / leverage, 4)

    # ストップ幅には、最初のエントリー時に計算したボラティリティを使う
    stop = flag["add-position"]["stop"]

    # 実際に購入可能な枚数を計算する
    able_lot = int(round(np.floor(balance * leverage / data["close_price"] * 100) / 100, -3))
    lot = min(able_lot, flag["add-position"]["unit-size"])

    flag["records"]["log"].append("証拠金から購入できる枚数は最大{}通貨までです\n".format(able_lot))
    return lot, stop, flag


# 複数回に分けて追加ポジションを取る関数
def add_position(data, flag):
    # ポジションがない場合は何もしない
    if flag["position"]["exist"] == False:
        return flag

    # 固定ロット（10000通貨）でのテスト時は何もしない
    if TEST_MODE_LOT == "fixed":
        return flag

    # 最初（１回目）のエントリー価格を記録
    if flag["add-position"]["count"] == 0:
        flag["add-position"]["first-entry-price"] = flag["position"]["price"]
        flag["add-position"]["last-entry-price"] = flag["position"]["price"]
        flag["add-position"]["count"] += 1

    while True:

        # 以下の場合は、追加ポジションを取らない
        if flag["add-position"]["count"] >= entry_times:
            return flag

        # この関数の中で使う変数を用意
        first_entry_price = flag["add-position"]["first-entry-price"]
        last_entry_price = flag["add-position"]["last-entry-price"]
        unit_range = flag["add-position"]["unit-range"]
        current_price = data["close_price"]

        # 価格がエントリー方向に基準レンジ分だけ進んだか判定する
        should_add_position = False
        if flag["position"]["side"] == "BUY" and (current_price - last_entry_price) > unit_range:
            should_add_position = True
        elif flag["position"]["side"] == "SELL" and (last_entry_price - current_price) > unit_range:
            should_add_position = True
        else:
            break

        # 基準レンジ分進んでいれば追加注文を出す
        if should_add_position == True:
            flag["records"]["log"].append(
                "\n前回のエントリー価格{0}円からブレイクアウトの方向に{1}ATR（{2}円）以上動きました\n".format(last_entry_price, entry_range,
                                                                            round(unit_range, 4)))
            flag["records"]["log"].append(
                "{0}/{1}回目の追加注文を出します\n".format(flag["add-position"]["count"] + 1, entry_times))

            # 注文サイズを計算
            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot < 0.01:
                flag["records"]["log"].append("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))
                flag["add-position"]["count"] += 1
                return flag

            # 追加注文を出す
            if flag["position"]["side"] == "BUY":
                entry_price = first_entry_price + (flag["add-position"]["count"] * unit_range)

                flag["records"]["log"].append("現在のポジションに追加して、{0}円で{1}通貨の買い注文を出します\n".format(entry_price, lot))

            # ここに買い注文のコードを入れる

            if flag["position"]["side"] == "SELL":
                entry_price = first_entry_price - (flag["add-position"]["count"] * unit_range)

                flag["records"]["log"].append("現在のポジションに追加して、{0}円で{1}通貨の売り注文を出します\n".format(entry_price, lot))

            # ここに売り注文のコードを入れる

            # ポジション全体の情報を更新する
            flag["position"]["stop"] = stop
            flag["position"]["price"] = float(round(
                (flag["position"]["price"] * flag["position"]["lot"] + entry_price * lot) / (
                            flag["position"]["lot"] + lot), 3))
            flag["position"]["lot"] = np.round((flag["position"]["lot"] + lot) * 100) / 100

            if flag["position"]["side"] == "BUY":
                flag["records"]["log"].append("{0}円の位置にストップを更新します\n".format(flag["position"]["price"] - stop))
            elif flag["position"]["side"] == "SELL":
                flag["records"]["log"].append("{0}円の位置にストップを更新します\n".format(flag["position"]["price"] + stop))

            flag["records"]["log"].append("現在のポジションの取得単価は{}円です\n".format(flag["position"]["price"]))
            flag["records"]["log"].append("現在のポジションサイズは{}通貨です\n\n".format(round(flag["position"]["lot"])))

            flag["add-position"]["count"] += 1
            flag["add-position"]["last-entry-price"] = entry_price

    return flag


# トレイリングストップの関数
def trail_stop(data, flag):
    # まだ追加ポジション（増し玉）の取得中であれば何もしない
    if flag["add-position"]["count"] < entry_times and TEST_MODE_LOT != "fixed":
        return flag

    # 高値／安値がエントリー価格からいくら離れたか計算
    if flag["position"]["side"] == "BUY":
        moved_range = data["high_price"] - flag["position"]["price"]
    if flag["position"]["side"] == "SELL":
        moved_range = flag["position"]["price"] - data["low_price"]

    # 最高値・最安値を更新したか調べる
    if moved_range < 0 or flag["position"]["stop-EP"] >= moved_range:
        return flag
    else:
        flag["position"]["stop-EP"] = moved_range

    # 加速係数に応じて損切りラインを動かす
    flag["position"]["stop"] = flag["position"]["stop"] - (moved_range + flag["position"]["stop"]) * flag["position"]["stop-AF"]

    # 加速係数を更新する
    flag["position"]["stop-AF"] = flag["position"]["stop-AF"] + stop_AF_add
    if flag["position"]["stop-AF"] >= stop_AF_max:
        flag["position"]["stop-AF"] = stop_AF_max

    # ログを出力する
    if flag["position"]["side"] == "BUY":
        flag["records"]["log"].append("トレイリングストップの発動：ストップ位置を{}円に動かして、加速係数を{}に更新します\n".format(
            round(flag["position"]["price"] - flag["position"]["stop"], 2), flag["position"]["stop-AF"]))
    else:
        flag["records"]["log"].append("トレイリングストップの発動：ストップ位置を{}円に動かして、加速係数を{}に更新します\n".format(
            round(flag["position"]["price"] + flag["position"]["stop"], 2), flag["position"]["stop-AF"]))

    return flag


# -------------価格APIの関数--------------
# oandaのapiを使用する関数
def get_price():
    api = API(access_token=token)
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    data = api.request(r)
    if data["candles"] is not None:
        price = [{"close_time": data["candles"][i]['time'],
                  "close_time_dt": dateutil.parser.parse(data["candles"][i]['time']).strftime('%Y/%m/%d %H:%M'),
                  "open_price": round(float(data["candles"][i]["mid"]['o']), 3),
                  "high_price": round(float(data["candles"][i]["mid"]['h']), 3),
                  "low_price": round(float(data["candles"][i]["mid"]['l']), 3),
                  "close_price": round(float(data["candles"][i]["mid"]['c']), 3)}
                 for i in range(params['count'])]
        return price
    else:
        flag["records"]["log"].append("データが存在しません")
        return None


def get_price_from_file(path):
    d = pd.read_csv(path)
    price = [{"close_time": d.loc[i, 'time'],
              "close_time_dt": d.loc[i, 'time'],
              "open_price": round(d.loc[i, 'o'], 3),
              "high_price": round(d.loc[i, 'h'], 3),
              "low_price": round(d.loc[i, 'l'], 3),
              "close_price": round(d.loc[i, 'c'], 3)}
             for i in range(len(d))]
    return price


# 時間と高値・安値をログに記録する関数
def log_price(data, flag):
    log = "時間： " + dateutil.parser.parse(data['close_time']).strftime('%Y/%m/%d %H:%M') + " 高値： " + str(data["high_price"])\
           + " 安値： " + str(data["low_price"]) + " 終値： " + str(data["close_price"]) + "\n"
    flag["records"]["log"].append(log)
    return flag


# -------------その他の補助関数--------------

# 時間と高値・安値・終値を表示する関数
def print_price(data):
    print("時間： " + dateutil.parser.parse(data['close_time']).strftime('%Y/%m/%d %H:%M')
          + " 始値： " + str(data['open_price'])
          + " 終値： " + str(data['close_price']))


# １期間の平均ボラティリティを計算する
def calculate_volatility(last_data):
    high_sum = sum(i["high_price"] for i in last_data[-1 * volatility_term:])
    low_sum = sum(i["low_price"] for i in last_data[-1 * volatility_term:])
    volatility = round((high_sum - low_sum) / volatility_term, 4)
    flag["records"]["log"].append("現在の{0}期間の平均ボラティリティは{1}円です\n".format(volatility_term, volatility))
    return volatility


# ------------バックテストの部分の関数--------------


# 各トレードのパフォーマンスを記録する関数
def records(flag, data, close_price, close_type=None):
    # 取引手数料等の計算
    entry_price = int(round(flag["position"]["price"] * flag["position"]["lot"]))
    exit_price = int(round(close_price * flag["position"]["lot"]))


    # 手仕舞った日時と保有期間を記録
    flag["records"]["date"].append(data["close_time_dt"])
    flag["records"]["holding-periods"].append(flag["position"]["count"])

    # 損切りにかかった回数をカウント
    if close_type == "STOP":
        flag["records"]["stop-count"].append(1)
    else:
        flag["records"]["stop-count"].append(0)

    # 値幅の計算
    buy_profit = exit_price - entry_price
    sell_profit = entry_price - exit_price

    # 利益が出てるかの計算
    if flag["position"]["side"] == "BUY":
        flag["records"]["side"].append("BUY")
        flag["records"]["profit"].append(buy_profit)
        flag["records"]["return"].append(round(buy_profit / entry_price * 100, 4))
        flag["records"]["funds"] = flag["records"]["funds"] + buy_profit
        if buy_profit > 0:
            log = str(buy_profit) + "円の利益です\n\n"
            flag["records"]["log"].append(log)
        else:
            log = str(buy_profit) + "円の損失です\n\n"
            flag["records"]["log"].append(log)

    if flag["position"]["side"] == "SELL":
        flag["records"]["side"].append("SELL")
        flag["records"]["profit"].append(sell_profit)
        flag["records"]["return"].append(round(sell_profit / entry_price * 100, 4))
        flag["records"]["funds"] = flag["records"]["funds"] + sell_profit
        if sell_profit > 0:
            log = str(sell_profit) + "円の利益です\n\n"
            flag["records"]["log"].append(log)
        else:
            log = str(sell_profit) + "円の損失です\n\n"
            flag["records"]["log"].append(log)

    return flag


# バックテストの集計用の関数
def backtest(flag):
    # 成績を記録したpandas DataFrameを作成
    records = pd.DataFrame({
        "Date": pd.to_datetime(flag["records"]["date"]),
        "Profit": flag["records"]["profit"],
        "Side": flag["records"]["side"],
        "Rate": flag["records"]["return"],
        "Stop": flag["records"]["stop-count"],
        "Periods": flag["records"]["holding-periods"],
    })

    # 連敗回数をカウントする
    consecutive_defeats = []
    defeats = 0
    for p in flag["records"]["profit"]:
        if p < 0:
            defeats += 1
        else:
            consecutive_defeats.append(defeats)
            defeats = 0

    # 総損益の列を追加する
    records["Gross"] = records.Profit.cumsum()

    # 資産推移の列を追加する
    records["Funds"] = records.Gross + start_funds

    # 最大ドローダウンの列を追加する
    records["Drawdown"] = records.Funds.cummax().subtract(records.Funds)
    records["DrawdownRate"] = round(records.Drawdown / records.Funds.cummax() * 100, 1)

    # 買いエントリーと売りエントリーだけをそれぞれ抽出する
    buy_records = records[records.Side.isin(["BUY"])]
    sell_records = records[records.Side.isin(["SELL"])]

    # 月別のデータを集計する
    records["月別集計"] = pd.to_datetime(records.Date.apply(lambda x: x.strftime('%Y/%m')))
    grouped = records.groupby("月別集計")

    month_records = pd.DataFrame({
        "Number": grouped.Profit.count(),
        "Gross": grouped.Profit.sum(),
        "Funds": grouped.Funds.last(),
        "Rate": round(grouped.Rate.mean(), 2),
        "Drawdown": grouped.Drawdown.max(),
        "Periods": grouped.Periods.mean()
    })

    print("バックテストの結果")
    print("-----------------------------------")
    print("買いエントリの成績")
    print("-----------------------------------")
    print("トレード回数       :  {}回".format(len(buy_records)))
    print("勝率               :  {}％".format(round(len(buy_records[buy_records.Profit > 0]) / len(buy_records) * 100, 1)))
    print("平均リターン       :  {}％".format(round(buy_records.Rate.mean(), 2)))
    print("総損益             :  {}円".format(buy_records.Profit.sum()))
    print("平均保有期間       :  {}足分".format(round(buy_records.Periods.mean(), 1)))
    print("損切りの回数       :  {}回".format(buy_records.Stop.sum()))

    print("-----------------------------------")
    print("売りエントリの成績")
    print("-----------------------------------")
    print("トレード回数       :  {}回".format(len(sell_records)))
    print("勝率               :  {}％".format(
        round(len(sell_records[sell_records.Profit > 0]) / len(sell_records) * 100, 1)))
    print("平均リターン       :  {}％".format(round(sell_records.Rate.mean(), 2)))
    print("総損益             :  {}円".format(sell_records.Profit.sum()))
    print("平均保有期間       :  {}足分".format(round(sell_records.Periods.mean(), 1)))
    print("損切りの回数       :  {}回".format(sell_records.Stop.sum()))

    print("-----------------------------------")
    print("総合の成績")
    print("-----------------------------------")
    print("全トレード数       :  {}回".format(len(records)))
    print("勝率               :  {}％".format(round(len(records[records.Profit > 0]) / len(records) * 100, 1)))
    print("平均リターン       :  {}％".format(round(records.Rate.mean(), 2)))
    print("平均保有期間       :  {}足分".format(round(records.Periods.mean(), 1)))
    print("損切りの回数       :  {}回".format(records.Stop.sum()))
    print("")
    print("最大の勝ちトレード :  {}円".format(records.Profit.max()))
    print("最大の負けトレード :  {}円".format(records.Profit.min()))
    print("最大連敗回数       :  {}回".format(max(consecutive_defeats)))
    print("最大ドローダウン   :  {0}円 / {1}％".format(-1 * records.Drawdown.max(),
                                             -1 * records.DrawdownRate.loc[records.Drawdown.idxmax()]))
    print("利益合計           :  {}円".format(records[records.Profit > 0].Profit.sum()))
    print("損失合計           :  {}円".format(records[records.Profit < 0].Profit.sum()))
    print("最終損益           :  {}円".format(records.Profit.sum()))
    print("")
    print("初期資金           :  {}円".format(start_funds))
    print("最終資金           :  {}円".format(records.Funds.iloc[-1]))
    print("運用成績           :  {}％".format(round(records.Funds.iloc[-1] / start_funds * 100), 2))
    print("-----------------------------------")
    print("各成績指標")
    print("-----------------------------------")
    # print("CAGR(年間成長率)         :  {}％".format(
    #     round((records.Funds.iloc[-1] / start_funds) ** (365 / time_period) * 100 - 100, 2)))
    print("MARレシオ                :  {}".format(
        round((records.Funds.iloc[-1] / start_funds - 1) * 100 / records.DrawdownRate.max(), 2)))
    print("シャープレシオ           :  {}".format(round(records.Rate.mean() / records.Rate.std(), 2)))
    print("プロフィットファクター   :  {}".format(
        round(records[records.Profit > 0].Profit.sum() / abs(records[records.Profit < 0].Profit.sum()), 2)))
    print("損益レシオ               :  {}".format(
        round(records[records.Profit > 0].Rate.mean() / abs(records[records.Profit < 0].Rate.mean()), 2)))
    print("-----------------------------------")
    print("月別の成績")

    for index, row in month_records.iterrows():
        print("-----------------------------------")
        print("{0}年{1}月の成績".format(index.year, index.month))
        print("-----------------------------------")
        print("トレード数         :  {}回".format(row.Number.astype(int)))
        print("月間損益           :  {}円".format(row.Gross.astype(int)))
        print("平均リターン       :  {}％".format(row.Rate))
        print("継続ドローダウン   :  {}円".format(-1 * row.Drawdown.astype(int)))
        print("月末資金           :  {}円".format(row.Funds.astype(int)))

    # 際立った損益を表示
    n = 1
    print("------------------------------------------")
    print("＋{}%を超えるトレードの回数  :  {}回".format(n, len(records[records.Rate > n])))
    print("------------------------------------------")
    for index, row in records[records.Rate > n].iterrows():
        print("{0}  |  {1}％  |  {2}".format(row.Date, round(row.Rate, 2), row.Side))
    print("------------------------------------------")
    print("－{}%を下回るトレードの回数  :  {}回".format(n, len(records[records.Rate < n * -1])))
    print("------------------------------------------")
    for index, row in records[records.Rate < n * -1].iterrows():
        print("{0}  |  {1}％  |  {2}".format(row.Date, round(row.Rate, 2), row.Side))

    # ログファイルの出力
    file = open("text./{0}-log.txt".format(datetime.now().strftime("%Y-%m-%d-%H-%M")), 'wt', encoding='utf-8')
    file.writelines(flag["records"]["log"])

    # 損益曲線をプロット
    plt.subplot(1, 2, 1)
    plt.plot(records.Date, records.Funds)
    plt.xlabel("Date")
    plt.ylabel("Balance")
    plt.xticks(rotation=50)  # X軸の目盛りを50度回転

    # リターン分布の相対度数表を作る
    plt.subplot(1, 2, 2)
    plt.hist(records.Rate, 50, rwidth=0.9)
    plt.axvline(x=0, linestyle="dashed", label="Return = 0")
    plt.axvline(records.Rate.mean(), color="orange", label="AverageReturn")
    plt.legend()  # 凡例を表示
    plt.show()


# ------------ここからメイン処理の記述--------------
# 価格チャートを取得
pd.plotting.register_matplotlib_converters()
# price = get_price()
price = get_price_from_file('csv/' + instrument + '_' + params['granularity'] + '_' + '2017.1.1' + '.csv')


last_data = []
need_term = max(buy_term, sell_term, volatility_term, MA_term, Long_EMA_term * 2)
i = 0
while i < len(price):

    # ドンチャンの判定に使う期間分の安値・高値データを準備する
    if len(last_data) < need_term:
        last_data.append(price[i])
        flag = log_price(price[i], flag)
        time.sleep(wait)
        i += 1
        continue

    data = price[i]
    flag = log_price(data, flag)

    # ポジションがある場合
    if flag["position"]["exist"]:

        # 終値がポジションと同じ方向に動いた場合
        # 買いなら（安値⇒高値）の順、売りなら（高値⇒安値）の順に適用

        if (flag["position"]["side"] == "BUY" and data["open_price"] < data["close_price"]) \
                or (flag["position"]["side"] == "SELL" and data["open_price"] > data["close_price"]):

            if stop_config != "OFF":
                flag = stop_position(data, flag)
            flag = close_position(data, last_data, flag)
            flag = add_position(data, flag)
            flag = trail_stop(data, flag)

        # 終値がポジションと逆の方向に動いた場合
        # 買いなら（高値⇒安値）の順、売りなら（安値⇒高値）の順に適用

        else:

            flag = add_position(data, flag)
            flag = trail_stop(data, flag)
            flag = stop_position(data, flag)
            flag = close_position(data, last_data, flag)

    # ポジションがない場合
    else:
        flag = entry_signal(data, last_data, flag)

    last_data.append(data)
    i += 1
    time.sleep(wait)

print("--------------------------")
print("テスト期間：")
print("開始時点 : " + str(price[0]["close_time_dt"]))
print("終了時点 : " + str(price[-1]["close_time_dt"]))
print(str(len(price)) + "件のローソク足データで検証")
print("--------------------------")

backtest(flag)
