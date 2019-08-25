import json


def Auth():
    accountID, token, line_token, TW_API_key, TW_API_secret_key, TW_Access_token, TW_Access_token_secret = \
        None, None, None, None, None, None, None
    f = open('config/default.json', 'r', encoding="utf-8")
    config = json.load(f)
    accountID = config["accountID"]
    token = config["token"]
    line_token = config["line_token"]
    TW_API_key = config["TW_API_key"]
    TW_API_secret_key = config["TW_API_secret_key"]
    TW_Access_token = config["TW_Access_token"]
    TW_Access_token_secret = config["TW_Access_token_secret"]
    return accountID, token, line_token, TW_API_key, TW_API_secret_key, TW_Access_token, TW_Access_token_secret
