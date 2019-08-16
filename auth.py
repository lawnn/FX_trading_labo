def exampleAuth():
    accountID, token, line_token = None, None, None
    with open("account.txt") as I:
        accountID = I.read().strip()
    with open("token.txt") as I:
        token = I.read().strip()
    with open("line_token.txt") as I:
        line_token = I.read().strip()
    return accountID, token, line_token
