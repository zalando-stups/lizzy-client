import tokens


def get_token(url: str, scopes: str, credentials_dir: str) -> dict:
    """
    Get access token info.
    """

    tokens.configure(url=url, dir=credentials_dir)
    tokens.manage('lizzy', [scopes])
    tokens.start()

    return tokens.get('lizzy')
