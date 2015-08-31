import pytest
from click.testing import CliRunner
from mock import MagicMock

from lizzy_client.cli import main, fetch_token
from lizzy_client.token import TokenException


def test_not_enough_parameters(monkeypatch):
    mock_lizzy = MagicMock()
    monkeypatch.setattr('lizzy_client.cli.Lizzy', mock_lizzy)

    runner = CliRunner()
    result = runner.invoke(main, ['delete'])

    assert 'Error: Missing argument' in result.output


def test_fetch_token(monkeypatch):
    mock_get_token = MagicMock()
    mock_get_token.return_value = '4CC3557OCC3N'
    monkeypatch.setattr('lizzy_client.cli.get_token', mock_get_token)

    token = fetch_token('https://example.com', ['scope'], 'test', 'test_secret', 'user', 'password')

    assert token == '4CC3557OCC3N'

    mock_get_token.side_effect = TokenException('Error')

    with pytest.raises(SystemExit) as exc_info:  # type: py.code.ExceptionInfo
        fetch_token('https://example.com', ['scope'], 'test', 'test_secret', 'user', 'password')

    exception = exc_info.value
    assert repr(exception) == 'SystemExit(1,)'
