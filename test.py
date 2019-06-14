from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
from auth import exampleAuth
from pprint import pprint

accountID, token = exampleAuth()
api = API(access_token=token)

# 5分間隔で5000データ
params = {
    "count": 10,
    "granularity": "H2"
}

r = instruments.InstrumentsCandles(instrument="USD_JPY", params=params)
api.request(r)

pprint(api.request(r))

#data = []
#for raw in r.response['candles']:
#    data.append([raw['time'], raw['volume'], raw['mid']['o'], raw['mid']['h'], raw['mid']['l'], raw['mid']['c']])

#print(data)