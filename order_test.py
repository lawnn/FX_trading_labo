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
    "units": "-2",
    "type": "MARKET",
    "positionFill": "DEFAULT"
  }
}
#注文実行
r = orders.OrderCreate(accountID, data=data)
rv = api.request(r)

pprint(rv)

# examle
# {'lastTransactionID': '38',
#  'orderCreateTransaction': {'accountID': '101-009-11452891-001',
#                             'batchID': '37',
#                             'id': '37',
#                             'instrument': 'USD_JPY',
#                             'positionFill': 'DEFAULT',
#                             'reason': 'CLIENT_ORDER',
#                             'requestID': '42595366173843970',
#                             'time': '2019-08-12T06:41:27.635685586Z',
#                             'timeInForce': 'FOK',
#                             'type': 'MARKET_ORDER',
#                             'units': '-2',
#                             'userID': 11452891},
#  'orderFillTransaction': {'accountBalance': '2999986.0740',
#                           'accountID': '101-009-11452891-001',
#                           'batchID': '37',
#                           'commission': '0.0000',
#                           'financing': '0.0000',
#                           'fullPrice': {'asks': [{'liquidity': '250000',
#                                                   'price': '105.425'}],
#                                         'bids': [{'liquidity': '250000',
#                                                   'price': '105.421'}],
#                                         'closeoutAsk': '105.444',
#                                         'closeoutBid': '105.402',
#                                         'timestamp': '2019-08-12T06:41:11.214530239Z'},
#                           'fullVWAP': '105.421',
#                           'gainQuoteHomeConversionFactor': '1',
#                           'guaranteedExecutionFee': '0.0000',
#                           'halfSpreadCost': '0.0040',
#                           'id': '38',
#                           'instrument': 'USD_JPY',
#                           'lossQuoteHomeConversionFactor': '1',
#                           'orderID': '37',
#                           'pl': '0.0000',
#                           'price': '105.421',
#                           'reason': 'MARKET_ORDER',
#                           'requestID': '42595366173843970',
#                           'requestedUnits': '-2',
#                           'time': '2019-08-12T06:41:27.635685586Z',
#                           'tradeOpened': {'guaranteedExecutionFee': '0.0000',
#                                           'halfSpreadCost': '0.0040',
#                                           'initialMarginRequired': '8.4338',
#                                           'price': '105.421',
#                                           'tradeID': '38',
#                                           'units': '-2'},
#                           'type': 'ORDER_FILL',
#                           'units': '-2',
#                           'userID': 11452891},
#  'relatedTransactionIDs': ['37', '38']}

