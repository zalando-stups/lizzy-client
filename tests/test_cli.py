import pytest
import os.path
import requests
from click.testing import CliRunner
from mock import MagicMock

from lizzy_client.cli import main, fetch_token
from lizzy_client.token import TokenException

test_dir = os.path.dirname(__file__)
config_path = os.path.join(test_dir, 'test_config.yaml')


class FakeLizzy:
    final_state = 'CF:CREATE_COMPLETE'
    raise_exception = False

    def __init__(self, base_url: str, access_token: str):
        pass

    @classmethod
    def reset(cls):
        cls.final_state = 'CF:CREATE_COMPLETE'
        cls.raise_exception = False

    def new_stack(self, image_version, keep_stacks, traffic, definition):
        if self.raise_exception:
            raise requests.HTTPError('404 Not Found')
        else:
            return '57ACC1D'

    def wait_for_deployment(self, stack_id: str) -> [str]:
        return ['CF:WAITING', self.final_state]


@pytest.fixture
def mock_get_token(monkeypatch):
    mock = MagicMock()
    mock.return_value = '4CC3557OCC3N'
    monkeypatch.setattr('lizzy_client.cli.get_token', mock)
    return mock


@pytest.fixture
def mock_fake_lizzy(monkeypatch):
    FakeLizzy.reset()
    monkeypatch.setattr('lizzy_client.cli.Lizzy', FakeLizzy)
    return FakeLizzy


def test_not_enough_parameters(monkeypatch):
    mock_lizzy = MagicMock()
    monkeypatch.setattr('lizzy_client.cli.Lizzy', mock_lizzy)

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(main, ['create', '-c', 'none', 'definition', 'version'])
        assert 'Error: Missing option' in result.output

    result = runner.invoke(main, ['delete'])
    assert 'Error: Missing argument' in result.output


def test_fetch_token(mock_get_token):
    token = fetch_token('https://example.com', ['scope'], 'test', 'test_secret', 'user', 'password')

    assert token == '4CC3557OCC3N'

    mock_get_token.side_effect = TokenException('Error')

    with pytest.raises(SystemExit) as exc_info:  # type: py.code.ExceptionInfo
        fetch_token('https://example.com', ['scope'], 'test', 'test_secret', 'user', 'password')

    exception = exc_info.value
    assert repr(exception) == 'SystemExit(1,)'


def test_create(mock_get_token, mock_fake_lizzy):
    runner = CliRunner()
    result = runner.invoke(main, ['create', '-c', config_path, config_path, '1.0'])
    assert 'Fetching authentication token.. . OK' in result.output
    assert 'Requesting new stack.. OK' in result.output
    assert 'Stack ID: 57ACC1D' in result.output
    assert 'Waiting for new stack... . . OK' in result.output
    assert 'Deployment Successful' in result.output

    result = runner.invoke(main, ['create', '-c', config_path, '-v', config_path, '1.0'])
    assert 'Fetching authentication token.. . OK' in result.output
    assert 'Requesting new stack.. OK' in result.output
    assert 'Stack ID: 57ACC1D' in result.output
    assert 'Waiting for new stack...\n' in result.output
    assert 'CF:WAITING' in result.output
    assert 'CF:CREATE_COMPLETE' in result.output
    assert 'Deployment Successful' in result.output

    FakeLizzy.final_state = 'CF:ROLLBACK_COMPLETE'
    result = runner.invoke(main, ['create', '-c', config_path, '-v', config_path, '1.0'])
    assert 'Stack was rollback after deployment. Check you application log for possible reasons.' in result.output

    FakeLizzy.final_state = 'LIZZY:REMOVED'
    result = runner.invoke(main, ['create', '-c', config_path, '-v', config_path, '1.0'])
    assert 'Stack was removed before deployment finished.' in result.output

    FakeLizzy.final_state = 'CF:CREATE_FAILED'
    result = runner.invoke(main, ['create', '-c', config_path, '-v', config_path, '1.0'])
    assert 'Deployment failed: CF:CREATE_FAILED.' in result.output

    FakeLizzy.reset()
    FakeLizzy.raise_exception = True
    result = runner.invoke(main, ['create', '-c', config_path, '-v', config_path, '1.0'])
    assert 'Deployment failed: 404 Not Found.' in result.output
