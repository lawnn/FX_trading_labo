import json


def Auth():
    accountID, token, line_token = None, None, None
    f = open('config/default.json', 'r', encoding="utf-8")
    config = json.load(f)
    accountID = config["accountID"]
    token = config["token"]
    line_token = config["line_token"]
    return accountID, token, line_token
