from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import pandas as pd
import time
from datetime import datetime
from auth import Auth


# start～endまでのデータ取得
def get_period_data(start, end, minute, instrument):
    timestamp = start.timestamp()
    concats = []
    count = 5000
    while True:
        df, last_timestamp = send_api(count, timestamp, minute, instrument)
        concats.append(df)
        if last_timestamp > end.timestamp() or len(df) < count:
            break
        timestamp = last_timestamp + (60 * minute)
    df = pd.concat(concats)
    if end is None:
        return df
    else:
        return df[df.index < end]


# 時間足のdfを取得
def send_api(count, start, minute, instrument):
    # oandaへのリクエストの送信
    global granularity
    api = API(access_token=token, environment="practice", headers={"Accept-Datetime-Format": "Unix"})
    if minute == 1:
        granularity = 'M1'
    elif minute == 5:
        granularity = 'M5'
    elif minute == 15:
        granularity = 'M15'
    elif minute == 30:
        granularity = 'M30'
    elif minute == 60:
        granularity = 'H1'
    elif minute == 120:
        granularity = 'H2'
    elif minute == 240:
        granularity = 'H4'
    elif minute == 480:
        granularity = 'H8'
    elif minute == 1440:
        granularity = 'D'
    params = {
        'count': count,
        'granularity': granularity,
    }
    if start is not None:
        params['from'] = start
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = api.request(r)
    time.sleep(5)

    # レスポンスの整形
    def join_json(candle):
        tmp = candle['mid']
        tmp['time'] = candle['time']
        tmp['v'] = candle['volume']
        tmp['complete'] = candle['complete']
        return tmp

    data_list = [join_json(candle) for candle in response['candles']]
    df = pd.DataFrame(data_list)
    last_timestamp = int(float(df.iloc[-1]['time']))

    # 型変更
    df['time'] = df['time'].astype('float64')
    df['o'] = df['o'].astype('float64')
    df['h'] = df['h'].astype('float64')
    df['l'] = df['l'].astype('float64')
    df['c'] = df['c'].astype('float64')
    df['v'] = df['v'].astype('float64')

    # タイムゾーンの変更、インデックス化
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['time'] = df['time'] + pd.Timedelta('09:00:00')  # 日本時間へ変換
    df.set_index('time', inplace=True)  # 時間をインデックスにする
    df = df.loc[:, ['o', 'h', 'l', 'c', 'v', 'complete']]  # 列の順番変更
    df = df.rename(columns={'o': 'o', 'h': 'h', 'l': 'l', 'c': 'c', 'v': 'volume'})

    return df, last_timestamp


accountID, token, line_token, TW_API_key, TW_API_secret_key, TW_Access_token, TW_Access_token_secret, \
    discord_webhook_url = Auth()
instrument = 'USD_JPY'
minute = [15]
# start = datetime.strptime('2017-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
# end = datetime.strptime('2019-06-01 00:00:00', '%Y-%m-%d %H:%M:%S')
# df = get_period_data(start, end, minute, instrument=instrument)
# print(df.to_json(orient="index"))
# df.to_csv(instrument + "_" + granularity + "_" + "2018" + ".csv")
# df.to_json("json/" + instrument + "_" + str(minute) + "_" + "2018" + ".json", orient="index")
for minute in minute:
    print('通貨【{0}】,時間軸{1}分のデータ取得中'.format(instrument, str(minute)))
    start = datetime.strptime('2017-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
    end = datetime.strptime('2019-08-15 00:00:00', '%Y-%m-%d %H:%M:%S')
    df = get_period_data(start, end, minute, instrument=instrument)
    df.to_csv('csv/' + instrument + "_" + granularity + "_" + "2017.1.1" + ".csv")
