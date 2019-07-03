from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
from datetime import datetime
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#-----設定項目
term = 30       # 過去n期間の設定
wait = 0        # ループの待機時間
lot = 10000     # 注文枚数
slippage = 0.0002  # 手数料・スリッページ


#oandaのapiを使用する関数
def get_price():
    price = [{"close_time": client.request(r)["candles"][i]['time'],
              "open_price": round(float(client.request(r)["candles"][i]["mid"]['o']), 3),
              "high_price": round(float(client.request(r)["candles"][i]["mid"]['h']), 3),
              "low_price": round(float(client.request(r)["candles"][i]["mid"]['l']), 3),
              "close_price": round(float(client.request(r)["candles"][i]["mid"]['c']), 3)}
             for i in range(params['count'])]
    return price


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
           + " 安値： " + str(data["low_price"]) + "\n"
    flag["records"]["log"].append(log)
    return flag


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
        flag["records"]["log"].append(
            "過去{0}足の最高値{1}円を、直近の高値が{2}円でブレイクしました\n".format(term, signal["price"], data["high_price"]))
        flag["records"]["log"].append(str(data["close_price"]) + "円で買いの指値注文を出します\n")

        # ここに買い注文のコードを入れる

        flag["order"]["exist"] = True
        flag["order"]["side"] = "BUY"
        flag["order"]["price"] = round(data["close_price"] * lot)

    if signal["side"] == "SELL":
        flag["records"]["log"].append(
            "過去{0}足の最安値{1}円を、直近の安値が{2}円でブレイクしました\n".format(term, signal["price"], data["low_price"]))
        flag["records"]["log"].append(str(data["close_price"]) + "円で売りの指値注文を出します\n")

        # ここに売り注文のコードを入れる

        flag["order"]["exist"] = True
        flag["order"]["side"] = "SELL"
        flag["order"]["price"] = round(data["close_price"] * lot)

    return flag


# サーバーに出した注文が約定したか確認する関数
def check_order(flag):
    # 注文状況を確認して通っていたら以下を実行
    # 一定時間で注文が通っていなければキャンセルする

    flag["order"]["exist"] = False
    flag["order"]["count"] = 0
    flag["position"]["exist"] = True
    flag["position"]["side"] = flag["order"]["side"]
    flag["position"]["price"] = flag["order"]["price"]

    return flag


# 手仕舞いのシグナルが出たら決済の成行注文 + ドテン注文 を出す関数
def close_position(data, last_data, flag):
    flag["position"]["count"] += 1
    signal = donchian(data, last_data)

    if flag["position"]["side"] == "BUY":
        if signal["side"] == "SELL":
            flag["records"]["log"].append(
                "過去{0}足の最安値{1}円を、直近の安値が{2}円でブレイクしました\n".format(term, signal["price"], data["low_price"]))
            flag["records"]["log"].append(str(data["close_price"]) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data)
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            flag["records"]["log"].append("さらに" + str(data["close_price"]) + "円で売りの指値注文を入れてドテンします\n")

            # ここに売り注文のコードを入れる

            flag["order"]["exist"] = True
            flag["order"]["side"] = "SELL"
            flag["order"]["price"] = round(data["close_price"] * lot)

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            flag["records"]["log"].append(
                "過去{0}足の最高値{1}円を、直近の高値が{2}円でブレイクしました\n".format(term, signal["price"], data["high_price"]))
            flag["records"]["log"].append(str(data["close_price"]) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data)
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            flag["records"]["log"].append("さらに" + str(data["close_price"]) + "円で買いの指値注文を入れてドテンします\n")

            # ここに買い注文のコードを入れる

            flag["order"]["exist"] = True
            flag["order"]["side"] = "BUY"
            flag["order"]["price"] = round(data["close_price"] * lot)

    return flag


# 各トレードのパフォーマンスを記録する関数
def records(flag, data):
    # 取引手数料等の計算
    entry_price = flag["position"]["price"]
    exit_price = round(data["close_price"] * lot)
    trade_cost = round(exit_price * slippage)

    log = "スリッページ・手数料として " + str(trade_cost) + "円を考慮します\n"
    flag["records"]["log"].append(log)
    flag["records"]["slippage"].append(trade_cost)

    # 手仕舞った日時と保有期間を記録
    flag["records"]["date"].append(data["close_time_dt"])
    flag["records"]["holding-periods"].append(flag["position"]["count"])

    # 値幅の計算
    buy_profit = exit_price - entry_price - trade_cost
    sell_profit = entry_price - exit_price - trade_cost

    # 利益が出てるかの計算
    if flag["position"]["side"] == "BUY":
        flag["records"]["side"].append("BUY")
        flag["records"]["profit"].append(buy_profit)
        flag["records"]["return"].append(round(buy_profit / entry_price * 100, 4))
        if buy_profit > 0:
            log = str(buy_profit) + "円の利益です\n"
            flag["records"]["log"].append(log)
        else:
            log = str(buy_profit) + "円の損失です\n"
            flag["records"]["log"].append(log)

    if flag["position"]["side"] == "SELL":
        flag["records"]["side"].append("SELL")
        flag["records"]["profit"].append(sell_profit)
        flag["records"]["return"].append(round(sell_profit / entry_price * 100, 4))
        if sell_profit > 0:
            log = str(sell_profit) + "円の利益です\n"
            flag["records"]["log"].append(log)
        else:
            log = str(sell_profit) + "円の損失です\n"
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
        "Periods": flag["records"]["holding-periods"],
        "Slippage": flag["records"]["slippage"]
    })

    # 総損益の列を追加する
    records["Gross"] = records.Profit.cumsum()

    # 最大ドローダウンの列を追加する
    records["Drawdown"] = records.Gross.cummax().subtract(records.Gross)
    records["DrawdownRate"] = round(records.Drawdown / records.Gross.cummax() * 100, 1)

    # 買いエントリーと売りエントリーだけをそれぞれ抽出する
    buy_records = records[records.Side.isin(["BUY"])]
    sell_records = records[records.Side.isin(["SELL"])]

    # 月別のデータを集計する
    records["月別集計"] = pd.to_datetime(records.Date.apply(lambda x: x.strftime('%Y/%m')))
    grouped = records.groupby("月別集計")

    month_records = pd.DataFrame({
        "Number": grouped.Profit.count(),
        "Gross": grouped.Profit.sum(),
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

    print("-----------------------------------")
    print("売りエントリの成績")
    print("-----------------------------------")
    print("トレード回数       :  {}回".format(len(sell_records)))
    print("勝率               :  {}％".format(
        round(len(sell_records[sell_records.Profit > 0]) / len(sell_records) * 100, 1)))
    print("平均リターン       :  {}％".format(round(sell_records.Rate.mean(), 2)))
    print("総損益             :  {}円".format(sell_records.Profit.sum()))
    print("平均保有期間       :  {}足分".format(round(sell_records.Periods.mean(), 1)))

    print("-----------------------------------")
    print("総合の成績")
    print("-----------------------------------")
    print("全トレード数       :  {}回".format(len(records)))
    print("勝率               :  {}％".format(round(len(records[records.Profit > 0]) / len(records) * 100, 1)))
    print("平均リターン       :  {}％".format(round(records.Rate.mean(), 2)))
    print("平均保有期間       :  {}足分".format(round(records.Periods.mean(), 1)))
    print("")
    print("最大の勝ちトレード :  {}円".format(records.Profit.max()))
    print("最大の負けトレード :  {}円".format(records.Profit.min()))
    print("最大ドローダウン   :  {0}円 / {1}％".format(-1 * records.Drawdown.max(),
                                             -1 * records.DrawdownRate.loc[records.Drawdown.idxmax()]))
    print("利益合計           :  {}円".format(records[records.Profit > 0].Profit.sum()))
    print("損失合計           :  {}円".format(records[records.Profit < 0].Profit.sum()))
    print("")
    print("最終損益           :  {}円".format(records.Profit.sum()))
    print("手数料合計         :  {}円".format(-1 * records.Slippage.sum()))

    print("-----------------------------------")
    print("月別の成績")

    for index, row in month_records.iterrows():
        print("-----------------------------------")
        print("{0}年{1}月の成績".format(index.year, index.month))
        print("-----------------------------------")
        print("トレード数         :  {}回".format(row.Number.astype(int)))
        print("月間損益           :  {}円".format(row.Gross.astype(int)))
        print("平均リターン       :  {}％".format(row.Rate))
        print("月間ドローダウン   :  {}円".format(-1 * row.Drawdown.astype(int)))

    # ログファイルの出力
    file = open("./{0}-log.txt".format(datetime.now().strftime("%Y-%m-%d-%H-%M")), 'wt', encoding='utf-8')
    file.writelines(flag["records"]["log"])

    # 損益曲線をプロット
    plt.plot(records.Date, records.Gross)
    plt.xlabel("Date")
    plt.ylabel("Balance")
    plt.xticks(rotation=50)  # X軸の目盛りを50度回転

    plt.show()

#oandaのapiを一度だけ取得する為に関数から出す
accountID, token = exampleAuth()
client = API(access_token=token)
instrument = "GBP_JPY"
params = {
    "count": 50,
    "granularity": "H1"
}
r = instruments.InstrumentsCandles(instrument=instrument, params=params)
#Use csv file
csv_path = 'csv/' + instrument + '_' + params['granularity'] + '_' + '2017.1.1' + '.csv'


# ------------------------------
# ここからメイン処理
# ------------------------------

#price = get_price
price = get_price_from_file(csv_path)

flag = {
    "order": {
        "exist": False,
        "side": "",
        "price": 0,
        "count": 0
    },
    "position": {
        "exist": False,
        "side": "",
        "price": 0,
        "count": 0
    },
    "records": {
        "date": [],
        "profit": [],
        "return": [],
        "side": [],
        "holding-periods": [],
        "slippage": [],
        "log": []
    }
}

last_data = []
i = 0
while i < len(price):

    # ドンチャンの判定に使う過去30足分の安値・高値データを準備する
    if len(last_data) < term:
        last_data.append(price[i])
        flag = log_price(price[i], flag)
        time.sleep(wait)
        i += 1
        continue

    data = price[i]
    flag = log_price(data, flag)

    if flag["order"]["exist"]:
        flag = check_order(flag)
    elif flag["position"]["exist"]:
        flag = close_position(data, last_data, flag)
    else:
        flag = entry_signal(data, last_data, flag)

    # 過去データを30個に保つために先頭を削除
    del last_data[0]
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
