import tokens


def get_token(url: str, scopes: str) -> dict:
    """
    Get access token info.
    """

    tokens.configure(url=url)
    tokens.manage('lizzy', [scopes])
    tokens.start()

    return tokens.get('lizzy')
