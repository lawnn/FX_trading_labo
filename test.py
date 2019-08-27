from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
from auth import Auth
from pprint import pprint

accountID, token, line_token, TW_API_key, TW_API_secret_key, TW_Access_token, TW_Access_token_secret, \
    discord_webhook_url = Auth()
api = API(access_token=token)

# H2間隔で10データ
params = {
    "count": 10,
    "granularity": "H2"
}

r = instruments.InstrumentsCandles(instrument="USD_JPY", params=params)
response = api.request(r)


pprint(float(response["candles"][1]["mid"]["c"]))

#data = []
#for raw in r.response['candles']:
#    data.append([raw['time'], raw['volume'], raw['mid']['o'], raw['mid']['h'], raw['mid']['l'], raw['mid']['c']])

#print(data)