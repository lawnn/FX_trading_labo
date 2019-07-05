from auth import exampleAuth
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import dateutil.parser
from datetime import datetime
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# -----設定項目
buy_term = 25              # 買いエントリーのブレイク期間の設定
sell_term = 25             # 売りエントリーのブレイク期間の設定

judge_price = {
  "BUY": "close_price",    # ブレイク判断　高値（high_price)か終値（close_price）を使用
  "SELL": "close_price"    # ブレイク判断　安値 (low_price)か終値（close_price）を使用
}

volatility_term = 30       # 平均ボラティリティの計算に使う期間
stop_range = 2             # 何レンジ幅に損切（ストップ）を置くか
trade_risk = 0.05          # 1トレードあたり口座の何％まで損失を許容するか
leverage = 5               # レバレッジ倍率の設定
start_funds = 500000       # シミュレーション時の初期資金

wait = 0                   # ループの待機時間
slippage = 0.0002          # 手数料・スリッページ


# oandaのapiを使用する関数
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


# 平均ボラティリティを計算する関数
def calculate_volatility(last_data):
    high_sum = sum(i["high_price"] for i in last_data[-1 * volatility_term:])
    low_sum = sum(i["low_price"] for i in last_data[-1 * volatility_term:])
    volatility = round((high_sum - low_sum) / volatility_term)
    flag["records"]["log"].append("現在の{0}期間の平均ボラティリティは{1}円です\n".format(volatility_term, volatility))
    return volatility


# 注文ロットを計算する関数
def calculate_lot(last_data, data, flag):
    lot = 0
    balance = flag["records"]["funds"]

    volatility = calculate_volatility(last_data)
    stop = stop_range * volatility

    calc_lot = np.floor(balance * trade_risk / stop * 100) / 100
    able_lot = np.floor(balance * leverage / data["close_price"] * 100) / 100
    lot = min(able_lot, calc_lot)

    flag["records"]["log"].append("現在のアカウント残高は{}円です\n".format(balance))
    flag["records"]["log"].append("許容リスクから購入できる枚数は最大{}BTCまでです\n".format(calc_lot))
    flag["records"]["log"].append("証拠金から購入できる枚数は最大{}BTCまでです\n".format(able_lot))

    return lot, stop


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
    signal = donchian(data, last_data)

    if signal["side"] == "BUY":
        flag["records"]["log"].append(
            "過去{0}足の最高値{1}円を、直近の価格が{2}円でブレイクしました\n".format(buy_term, signal["price"], data[judge_price["BUY"]]))

        lot, stop = calculate_lot(last_data, data, flag)
        if lot > 0.01:
            flag["records"]["log"].append("{0}円で{1}BTCの買い注文を出します\n".format(data["close_price"], lot))

            # ここに買い注文のコードを入れる

            flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] - stop))
            flag["order"]["lot"], flag["order"]["stop"] = lot, stop
            flag["order"]["exist"] = True
            flag["order"]["side"] = "BUY"
            flag["order"]["price"] = data["close_price"]
        else:
            flag["records"]["log"].append("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))

    if signal["side"] == "SELL":
        flag["records"]["log"].append(
            "過去{0}足の最安値{1}円を、直近の価格が{2}円でブレイクしました\n".format(sell_term, signal["price"], data[judge_price["SELL"]]))

        lot, stop = calculate_lot(last_data, data, flag)
        if lot > 0.01:
            flag["records"]["log"].append("{0}円で{1}BTCの売り注文を出します\n".format(data["close_price"], lot))

            # ここに売り注文のコードを入れる

            flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] + stop))
            flag["order"]["lot"], flag["order"]["stop"] = lot, stop
            flag["order"]["exist"] = True
            flag["order"]["side"] = "SELL"
            flag["order"]["price"] = data["close_price"]
        else:
            flag["records"]["log"].append("注文可能枚数{}が、最低注文単位に満たなかったので注文を見送ります\n".format(lot))

    return flag


# サーバーに出した注文が約定したか確認する関数
def check_order(flag):
    # 注文状況を確認して通っていたら以下を実行
    # 一定時間で注文が通っていなければキャンセルする

    flag["order"]["exist"] = False
    flag["order"]["count"] = 0
    flag["position"]["exist"] = True
    flag["position"]["side"] = flag["order"]["side"]
    flag["position"]["stop"] = flag["order"]["stop"]
    flag["position"]["price"] = flag["order"]["price"]
    flag["position"]["lot"] = flag["order"]["lot"]

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

            lot, stop = calculate_lot(last_data, data, flag)
            if lot > 0.01:
                flag["records"]["log"].append("さらに{0}円で{1}BTCの売りの注文を入れてドテンします\n".format(data["close_price"], lot))

                # ここに売り注文のコードを入れる

                flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] + stop))
                flag["order"]["lot"], flag["order"]["stop"] = lot, stop
                flag["order"]["exist"] = True
                flag["order"]["side"] = "SELL"
                flag["order"]["price"] = data["close_price"]

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            flag["records"]["log"].append(
                "過去{0}足の最高値{1}円を、直近の価格が{2}円でブレイクしました\n".format(buy_term, signal["price"], data[judge_price["BUY"]]))
            flag["records"]["log"].append(str(data["close_price"]) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data, data["close_price"])
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            lot, stop = calculate_lot(last_data, data, flag)
            if lot > 0.01:
                flag["records"]["log"].append("さらに{0}円で{1}BTCの買いの注文を入れてドテンします\n".format(data["close_price"], lot))

                # ここに買い注文のコードを入れる

                flag["records"]["log"].append("{0}円にストップを入れます\n".format(data["close_price"] - stop))
                flag["order"]["lot"], flag["order"]["stop"] = lot, stop
                flag["order"]["exist"] = True
                flag["order"]["side"] = "BUY"
                flag["order"]["price"] = data["close_price"]

    return flag


# 損切ラインにかかったら成行注文で決済する関数
def stop_position(data, flag):
    if flag["position"]["side"] == "BUY":
        stop_price = flag["position"]["price"] - flag["position"]["stop"]
        if data["low_price"] < stop_price:
            flag["records"]["log"].append("{0}円の損切ラインに引っかかりました。\n".format(stop_price))
            stop_price = flag["position"]["price"] - flag["position"]["ATR"] * stop_range
            flag["records"]["log"].append(str(stop_price) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data, stop_price, "STOP")
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

    if flag["position"]["side"] == "SELL":
        stop_price = flag["position"]["price"] + flag["position"]["stop"]
        if data["high_price"] > stop_price:
            flag["records"]["log"].append("{0}円の損切ラインに引っかかりました。\n".format(stop_price))
            stop_price = flag["position"]["price"] - flag["position"]["ATR"] * stop_range
            flag["records"]["log"].append(str(stop_price) + "円あたりで成行注文を出してポジションを決済します\n")

            # 決済の成行注文コードを入れる

            records(flag, data, stop_price, "STOP")
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

    return flag


# ------------バックテストの部分の関数--------------


# 各トレードのパフォーマンスを記録する関数
def records(flag, data, close_price, close_type=None):
    # 取引手数料等の計算
    entry_price = int(round(flag["position"]["price"] * flag["position"]["lot"]))
    exit_price = int(round(close_price * flag["position"]["lot"]))
    trade_cost = round(exit_price * slippage)

    log = "スリッページ・手数料として " + str(trade_cost) + "円を考慮します\n"
    flag["records"]["log"].append(log)
    flag["records"]["slippage"].append(trade_cost)

    # 手仕舞った日時と保有期間を記録
    flag["records"]["date"].append(data["close_time_dt"])
    flag["records"]["holding-periods"].append(flag["position"]["count"])

    # 損切りにかかった回数をカウント
    if close_type == "STOP":
        flag["records"]["stop-count"].append(1)
    else:
        flag["records"]["stop-count"].append(0)

    # 値幅の計算
    buy_profit = exit_price - entry_price - trade_cost
    sell_profit = entry_price - exit_price - trade_cost

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
        "Slippage": flag["records"]["slippage"]
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
        print("継続ドローダウン   :  {}円".format(-1 * row.Drawdown.astype(int)))
        print("月末資金           :  {}円".format(row.Funds.astype(int)))

    # ログファイルの出力
    file = open("./{0}-log.txt".format(datetime.now().strftime("%Y-%m-%d-%H-%M")), 'wt', encoding='utf-8')
    file.writelines(flag["records"]["log"])

    # 損益曲線をプロット
    plt.plot(records.Date, records.Funds)
    plt.xlabel("Date")
    plt.ylabel("Balance")
    plt.xticks(rotation=50)  # X軸の目盛りを50度回転

    plt.show()


# oandaのapiを一度だけ取得する為に関数から出す
accountID, token = exampleAuth()
client = API(access_token=token)
instrument = "EUR_JPY"
params = {
    "count": 50,
    "granularity": "H2"
}
r = instruments.InstrumentsCandles(instrument=instrument, params=params)
# Use csv file
csv_path = 'csv/' + instrument + '_' + params['granularity'] + '_' + '2017.1.1' + '.csv'


# ------------------------------
# ここからメイン処理
# ------------------------------

# price = get_price
price = get_price_from_file(csv_path)

flag = {
    "order": {
        "exist": False,
        "side": "",
        "price": 0,
        "ATR": 0,
        "count": 0
    },
    "position": {
        "exist": False,
        "side": "",
        "price": 0,
        "ATR": 0,
        "count": 0
    },
    "records": {
        "date": [],
        "profit": [],
        "return": [],
        "side": [],
        "stop-count": [],
        "funds": start_funds,
        "holding-periods": [],
        "slippage": [],
        "log": []
    }
}

last_data = []
need_term = max(buy_term, sell_term, volatility_term)
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

    if flag["order"]["exist"]:
        flag = check_order(flag)
    elif flag["position"]["exist"]:
        flag = stop_position(data, flag)
        flag = close_position(data, last_data, flag)
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
