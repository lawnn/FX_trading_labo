from auth import Auth
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
from pprint import pprint
accountID, token, line_token, TW_API_key, TW_API_secret_key, TW_Access_token, TW_Access_token_secret, \
    discord_webhook_url = Auth()
client = oandapyV20.API(access_token=token)
r = accounts.AccountSummary(accountID)
rv = client.request(r)
balance = rv['account']['balance']
print('現在の口座残高は{}円です。'.format(round(float(balance))))
pprint(rv)
