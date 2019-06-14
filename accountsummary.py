from auth import exampleAuth
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
from pprint import pprint
accountID, token = exampleAuth()
client = oandapyV20.API(access_token=token)
r = accounts.AccountSummary(accountID)
client.request(r)
pprint(r.response)
