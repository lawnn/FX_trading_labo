from auth import exampleAuth
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
from pprint import pprint
accountID, token = exampleAuth()
client = oandapyV20.API(access_token=token)
r = accounts.AccountSummary(accountID)
rv = client.request(r)
balance = rv['account']['balance']
print('現在の口座残高は{}円です。'.format(round(float(balance))))
pprint(rv)
