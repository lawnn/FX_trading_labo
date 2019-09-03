import json


def Auth():
    f = open('config/default.json', 'r', encoding="utf-8")
    config = json.load(f)

    try:
        accountID = config["accountID"]
        token = config["token"]
        line_token = config["line_token"]
        TW_API_key = config["TW_API_key"]
        TW_API_secret_key = config["TW_API_secret_key"]
        TW_Access_token = config["TW_Access_token"]
        TW_Access_token_secret = config["TW_Access_token_secret"]
        discord_webhook_url = config["discord_webhook_url"]
    except:
        accountID = None
        token = None
        line_token = None
        TW_API_key = None
        TW_API_secret_key = None
        TW_Access_token = None
        TW_Access_token_secret = None
        discord_webhook_url = None

    return accountID, token, line_token, TW_API_key, TW_API_secret_key, TW_Access_token, TW_Access_token_secret, \
           discord_webhook_url
