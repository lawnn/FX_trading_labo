from auth import exampleAuth
import requests
from logging import getLogger, Formatter, StreamHandler, FileHandler, INFO
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
from datetime import datetime
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# -------------設定項目------------------------

wait = 0  # ループの待機時間
buy_term = 10  # 買いエントリーのブレイク期間の設定
sell_term = 10  # 売りエントリーのブレイク期間の設定

judge_price = {
    "BUY": "high_price",  # ブレイク判断　高値（high_price)か終値（close_price）を使用
    "SELL": "low_price"  # ブレイク判断　安値 (low_price)か終値（close_price）を使用
}

TEST_MODE_LOT = "adjustable"  # fixed なら常に1通貨固定 / adjustable なら可変ロット
volatility_term = 4  # 平均ボラティリティの計算に使う期間
stop_range = 11  # 何レンジ幅に損切（ストップ）を置くか
trade_risk = 0.05  # 1トレードあたり口座の何％まで損失を許容するか
leverage = 25  # レバレッジ倍率の設定
start_funds = 500000  # シミュレーション時の初期資金

entry_times = 4  # 何回に分けて追加ポジションを取るか
entry_range = 0.5  # 何レンジごとに追加ポジションを取るか

stop_config = "TRAILING"  # ON / OFF / TRAILING の３つが設定可
stop_AF = 0.01  # 加速係数
stop_AF_add = 0.01  # 加速係数を増やす度合
stop_AF_max = 0.1  # 加速係数の上限

filter_VER = "OFF"  # フィルター設定／OFFで無効
MA_term = 30  # トレンドフィルターに使う移動平均線の期間
Short_EMA_term = 7
Long_EMA_term = Short_EMA_term * 2

line_config = "ON"  # LINE通知をするかどうかの設定
log_config = "ON"  # ログファイルを出力するかの設定
log_file_path = "c:/Pydoc/OANDA_donchanBOT.log"  # ログを記録するファイル名と出力パス

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

# -------------ログ機能の設定--------------------

# ログ機能の設定箇所
if log_config == "ON":
    logger = getLogger(__name__)
    handlerSh = StreamHandler()
    handlerFile = FileHandler(log_file_path)
    handlerSh.setLevel(INFO)
    handlerFile.setLevel(INFO)
    logger.setLevel(INFO)
    logger.addHandler(handlerSh)
    logger.addHandler(handlerFile)

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
        print_log(
            "過去{0}足の最高値{1}円を、直近の価格が{2}円でブレイクしました\n".format(buy_term, signal["price"], data[judge_price["BUY"]]))
        # フィルター条件を確認
        if filter(signal) == False:
            print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません\n")
            return flag

        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot > 0.01:
            print_log("{0}円で{1}通貨の買い注文を出します\n".format(data["close_price"], lot))

            # ここに買い注文のコードを入れる

            print_log("{0}円にストップを入れます\n".format(data["close_price"] - stop))
            flag["position"]["lot"], flag["position"]["stop"] = lot, stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "BUY"
            flag["position"]["price"] = data["close_price"]
        else:
            print_log("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))

    if signal["side"] == "SELL":
        print_log(
            "過去{0}足の最安値{1}円を、直近の価格が{2}円でブレイクしました\n".format(sell_term, signal["price"], data[judge_price["SELL"]]))

        # フィルター条件を確認
        if filter(signal) == False:
            print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません\n")
            return flag

        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot > 0.01:
            print_log("{0}円で{1}通貨の売り注文を出します\n".format(data["close_price"], lot))

            # ここに売り注文のコードを入れる

            print_log("{0}円にストップを入れます\n".format(data["close_price"] + stop))
            flag["position"]["lot"], flag["position"]["stop"] = lot, stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "SELL"
            flag["position"]["price"] = data["close_price"]
        else:
            print_log("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))

    return flag


# 損切ラインにかかったら成行注文で決済する関数
def stop_position(data, flag):
    # トレイリングストップを実行
    if stop_config == "TRAILING":
        flag = trail_stop(data, flag)

    if flag["position"]["side"] == "BUY":
        stop_price = flag["position"]["price"] - flag["position"]["stop"]
        if data["low_price"] < stop_price:
            print_log("{0}円の損切ラインに引っかかりました。\n".format(stop_price))
            stop_price = round(stop_price - 4 * calculate_volatility(last_data) / (chart_sec / 60), 4)
            print_log(str(stop_price) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

    if flag["position"]["side"] == "SELL":
        stop_price = flag["position"]["price"] + flag["position"]["stop"]
        if data["high_price"] > stop_price:
            print_log("{0}円の損切ラインに引っかかりました。\n".format(stop_price))
            stop_price = round(stop_price + 4 * calculate_volatility(last_data) / (chart_sec / 60), 4)
            print_log(str(stop_price) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

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
            print_log(
                "過去{0}足の最安値{1}円を、直近の価格が{2}円でブレイクしました\n".format(sell_term, signal["price"], data[judge_price["SELL"]]))
            print_log(str(data["close_price"]) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            # ドテン注文の箇所
            # フィルター条件を確認
            if filter(signal) == False:
                print_log("フィルターのエントリー条件を満たさなかったため、ドテンエントリーはしません\n")
                return flag

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot >= 0.01:
                print_log("\n{0}円で{1}通貨の売りの注文を入れてドテンします\n".format(data["close_price"], lot))

                # ここに売り注文のコードを入れる

                print_log("{0}円にストップを入れます\n".format(data["close_price"] + stop))
                flag["position"]["lot"], flag["position"]["stop"] = lot, stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "SELL"
                flag["position"]["price"] = data["close_price"]

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            print_log(
                "過去{0}足の最高値{1}円を、直近の価格が{2}円でブレイクしました\n".format(buy_term, signal["price"], data[judge_price["BUY"]]))
            print_log(str(data["close_price"]) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            # ドテン注文の箇所
            # フィルター条件を確認
            if filter(signal) == False:
                print_log("フィルターのエントリー条件を満たさなかったため、ドテンエントリーはしません\n")
                return flag

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot > 0.01:
                print_log("\n{0}円で{1}通貨の買いの注文を入れてドテンします\n".format(data["close_price"], lot))

                # ここに買い注文のコードを入れる

                print_log("{0}円にストップを入れます\n".format(data["close_price"] - stop))
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
        if len(last_data) < Long_EMA_term * 2:
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

        print_log("\n現在のアカウント残高は{}円です\n".format(balance))
        print_log("許容リスクから購入できる枚数は最大{}通貨までです\n".format(calc_lot))
        print_log("{0}回に分けて{1}通貨ずつ注文します\n".format(entry_times, flag["add-position"]["unit-size"]))

    # ストップ幅には、最初のエントリー時に計算したボラティリティを使う
    stop = flag["add-position"]["stop"]

    # 実際に購入可能な枚数を計算する
    able_lot = int(round(np.floor(balance * leverage / data["close_price"] * 100) / 100, -3))
    lot = min(able_lot, flag["add-position"]["unit-size"])

    print_log("証拠金から購入できる枚数は最大{}通貨までです\n".format(able_lot))
    return lot, stop, flag


# 複数回に分けて追加ポジションを取る関数
def add_position(data, flag):
    # ポジションがない場合は何もしない
    if flag["position"]["exist"] == False:
        return flag

    # 最初（１回目）のエントリー価格を記録
    if flag["add-position"]["count"] == 0:
        flag["add-position"]["first-entry-price"] = flag["position"]["price"]
        flag["add-position"]["last-entry-price"] = flag["position"]["price"]
        flag["add-position"]["count"] += 1

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

    # 基準レンジ分進んでいれば追加注文を出す
    if should_add_position == True:
        print_log(
            "\n前回のエントリー価格{0}円からブレイクアウトの方向に{1}ATR（{2}円）以上動きました\n".format(last_entry_price, entry_range,
                                                                        round(unit_range, 4)))
        print_log(
            "{0}/{1}回目の追加注文を出します\n".format(flag["add-position"]["count"] + 1, entry_times))

        # 注文サイズを計算
        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot < 0.01:
            print_log("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))
            flag["add-position"]["count"] += 1
            return flag

        # 追加注文を出す
        if flag["position"]["side"] == "BUY":
            entry_price = first_entry_price + (flag["add-position"]["count"] * unit_range)

            print_log("現在のポジションに追加して、{0}円で{1}通貨の買い注文を出します\n".format(entry_price, lot))

        # ここに買い注文のコードを入れる

        if flag["position"]["side"] == "SELL":
            entry_price = first_entry_price - (flag["add-position"]["count"] * unit_range)

            print_log("現在のポジションに追加して、{0}円で{1}通貨の売り注文を出します\n".format(entry_price, lot))

        # ここに売り注文のコードを入れる

        # ポジション全体の情報を更新する
        flag["position"]["stop"] = stop
        flag["position"]["price"] = float(round(
            (flag["position"]["price"] * flag["position"]["lot"] + entry_price * lot) / (
                    flag["position"]["lot"] + lot), 3))
        flag["position"]["lot"] = np.round((flag["position"]["lot"] + lot) * 100) / 100

        if flag["position"]["side"] == "BUY":
            print_log("{0}円の位置にストップを更新します\n".format(flag["position"]["price"] - stop))
        elif flag["position"]["side"] == "SELL":
            print_log("{0}円の位置にストップを更新します\n".format(flag["position"]["price"] + stop))

        print_log("現在のポジションの取得単価は{}円です\n".format(flag["position"]["price"]))
        print_log("現在のポジションサイズは{}通貨です\n\n".format(round(flag["position"]["lot"])))

        flag["add-position"]["count"] += 1
        flag["add-position"]["last-entry-price"] = entry_price

    return flag


# トレイリングストップの関数
def trail_stop(data, flag):
    # まだ追加ポジション（増し玉）の取得中であれば何もしない
    if flag["add-position"]["count"] < entry_times:
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
    flag["position"]["stop"] = flag["position"]["stop"] - (moved_range + flag["position"]["stop"]) * flag["position"][
        "stop-AF"]

    # 加速係数を更新
    flag["position"]["stop-AF"] = flag["position"]["stop-AF"] + stop_AF_add
    if flag["position"]["stop-AF"] >= stop_AF_max:
        flag["position"]["stop-AF"] = stop_AF_max

    # ログ出力
    if flag["position"]["side"] == "BUY":
        print_log("トレイリングストップの発動：ストップ位置を{}円に動かして、加速係数を{}に更新します\n".format(
            round(flag["position"]["price"] - flag["position"]["stop"], 2), flag["position"]["stop-AF"]))
    else:
        print_log("トレイリングストップの発動：ストップ位置を{}円に動かして、加速係数を{}に更新します\n".format(
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
        print_log("データが存在しません")
        return None


# OANDAのチャート価格をAPIで取得する関数（リアルタイム用）
def get_realtime_price():
    instrument = "USD_JPY"
    params = {
        "count": 5000,
        "granularity": "M15"
    }
    while True:
        try:
            api = API(access_token=token)
            r = instruments.InstrumentsCandles(instrument=instrument, params=params)
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
            print_log("OANDAの価格取得でエラー発生 : " + str(e))
            print_log("{}秒待機してやり直します".format(wait))
            time.sleep(wait)


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
    print_log("現在の{0}期間の平均ボラティリティは{1}円です\n".format(volatility_term, volatility))
    return volatility


# ログファイルの出力やLINE通知の関数
def print_log(text):
    # LINE通知する場合
    if line_config == "ON":
        url = "https://notify-api.line.me/api/notify"
        data = {"message": str(text)}
        headers = {"Authorization": "Bearer " + line_token}
        try:
            requests.post(url, data=data, headers=headers)
        except requests.exceptions.RequestException as e:
            if log_config == "ON":
                logger.info(str(e))
            else:
                print(str(e))

    # コマンドラインへの出力とファイル保存
    if log_config == "ON":
        logger.info(text)
    else:
        print(text)


# ------------ここからメイン処理の記述--------------

# 最低限、保持が必要なローソク足の期間を準備

need_term = max(buy_term, sell_term, volatility_term, MA_term, Long_EMA_term * 2)
print_log("{}期間分のデータの準備中".format(need_term))

price = get_price()
last_data = price[-1 * need_term - 2:-2]
print_price(last_data[-1])
print_log("--{}秒待機--".format(wait))
time.sleep(wait)

print_log("---実行開始---")

while True:

    # 最新のローソク足を取得して表示
    data = get_realtime_price()
    if data["settled"]["close_time"] > last_data[-1]["close_time"]:
        print_price(data["settled"])

    # ポジションがある場合
    if flag["position"]["exist"]:
        flag = stop_position(data, flag)
        flag = close_position(data, last_data, flag)
        flag = add_position(data, flag)

    # ポジションがない場合
    else:
        flag = entry_signal(data, last_data, flag)

    # 確定足が更新された場合
    if data["settled"]["close_time"] > last_data[-1]["close_time"]:
        last_data.append(data["settled"])
        if len(last_data) > need_term:
            del last_data[0]

    time.sleep(wait)