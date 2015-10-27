from requests import Response
from tokens import InvalidCredentialsError
import json
import pytest
from lizzy_client.token import get_token


class FakeResponse(Response):
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: ste
        """
        self.status_code = status_code
        self.reason = 'REASON NOT SET IN MOCK'
        self._content = text

    def json(self):
        return json.loads(self.content)


def test_get_token(monkeypatch):
    monkeypatch.setattr('os.environ', {'OAUTH2_ACCESS_TOKENS': 'lizzy=4CCE5570K3N'})
    access_token = get_token('https://token.example', scopes=['scope'], credentials_dir='/meta/credentials')
    assert access_token == '4CCE5570K3N'


def test_bad_config(monkeypatch):
    with pytest.raises(InvalidCredentialsError) as exc_info:
        get_token('https://token.example', scopes=['scope'], credentials_dir='/meta/credentials')

    exception = exc_info.value
    assert str(exception).startswith("Invalid OAuth credentials:")
