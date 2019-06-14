from auth import exampleAuth
import oandapyV20
import oandapyV20.endpoints.orders as orders
from pprint import pprint
#API取得
accountID, token = exampleAuth()
api = oandapyV20.API(access_token=token)
#注文内容
data = {
  "order": {
    #"price": "100.550",
    "instrument": "USD_JPY",
    "units": "1000",
    "type": "MARKET",
    "positionFill": "DEFAULT"
  }
}
#注文実行
r = orders.OrderCreate(accountID, data=data)
api.request(r)

pprint(r.response)
