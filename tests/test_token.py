from unittest.mock import MagicMock
from requests import Response
import json
import pytest

from lizzy_client.token import get_token, AuthenticationError, TokenInfoError


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
    mock_post = MagicMock()
    mock_post.return_value = FakeResponse(200, '{"access_token":"4CCE5570K3N"}')
    monkeypatch.setattr('requests.post', mock_post)

    access_token = get_token('https://token.example', scopes=['scope'], client_id='id', client_secret='secret',
                             user='user', password='password')

    mock_post.assert_called_once_with(auth=('id', 'secret'), url='https://token.example',
                                      data={'username': 'user', 'scope': ['scope'], 'password': 'password',
                                            'grant_type': 'password'})
    assert access_token == '4CCE5570K3N'


def test_bad_response(monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value = FakeResponse(200, '{"bad":"key"}')
    monkeypatch.setattr('requests.post', mock_post)

    with pytest.raises(TokenInfoError) as exc_info:
        get_token('https://token.example', scopes=['scope'], client_id='id', client_secret='secret',
                  user='user', password='password')

    exception = exc_info.value
    assert str(exception) == '"access_token" not on json.'


def test_client_error(monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value = FakeResponse(401, '{"access_token":"4CCE5570K3N"}')
    monkeypatch.setattr('requests.post', mock_post)

    with pytest.raises(AuthenticationError) as exc_info:
        get_token('https://token.example', scopes=['scope'], client_id='id', client_secret='secret',
                  user='user', password='password')

    exception = exc_info.value
    assert str(exception) == '401 Client Error: REASON NOT SET IN MOCK'


def test_server_error(monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value = FakeResponse(500, '{"access_token":"4CCE5570K3N"}')
    monkeypatch.setattr('requests.post', mock_post)

    with pytest.raises(AuthenticationError) as exc_info:
        get_token('https://token.example', scopes=['scope'], client_id='id', client_secret='secret',
                  user='user', password='password')

    exception = exc_info.value
    assert str(exception) == '500 Server Error: REASON NOT SET IN MOCK'
