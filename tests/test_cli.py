import pytest
import os.path
import requests
import json
from click.testing import CliRunner
from unittest.mock import MagicMock
from tokens import InvalidCredentialsError
from urlpath import URL

from lizzy_client.cli import main, fetch_token
from lizzy_client.version import VERSION, MAJOR_VERSION, MINOR_VERSION
from lizzy_client.lizzy import Lizzy

test_dir = os.path.dirname(__file__)
config_path = os.path.join(test_dir, 'test_config.yaml')

FAKE_ENV = {'OAUTH2_ACCESS_TOKEN_URL': 'oauth.example.com',
            'LIZZY_URL': 'lizzy.example.com'}


class FakeResponse(requests.Response):
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: str
        """
        self.status_code = status_code
        self._content = text
        self.raise_for_status = MagicMock()
        self.headers = {}

    def json(self):
        return json.loads(self.content)


class FakeLizzy(Lizzy):
    final_state = 'CREATE_COMPLETE'
    raise_exception = False
    traffic = MagicMock()
    delete = MagicMock()

    def __init__(self, base_url: str, access_token: str):
        self.access_token = "TOKEN"
        self.base_url = URL('https://localhost')

    @classmethod
    def reset(cls):
        cls.final_state = 'CREATE_COMPLETE'
        cls.raise_exception = False
        cls.delete.reset_mock()
        cls.traffic.reset_mock()

    def wait_for_deployment(self, stack_id: str) -> [str]:
        return ['CF:WAITING', self.final_state]


@pytest.fixture()
def mock_lizzy_get(monkeypatch):
    mock_get = MagicMock()
    stack1 = {'stack_name': 'stack1',
              "description": "stack1 (ImageVersion: 257)",
              'version': 's1',
              'status': 'CREATE_COMPLETE',
              'creation_time': '2016-01-01T12:00:00Z'}
    stack2 = {'stack_name': 'stack2',
              'version': 's2',
              "description": "stack1 (ImageVersion: 257)",
              'status': 'CF:TEST',
              'creation_time': '2015-12-01T12:00:00Z'}

    stack3 = {'stack_name': 'stack1',
              'version': 's42',
              "description": "stack1 (ImageVersion: 257)",
              'status': 'CREATE_COMPLETE',
              'creation_time': '2015-12-01T15:00:00Z'}

    stack4 = {'stack_name': 'stack1',
              'version': 's7',
              "description": "stack1 (ImageVersion: 257)",
              'status': 'CREATE_COMPLETE',
              'creation_time': '2016-01-01T10:00:00Z'}
    mock_get.return_value = FakeResponse(200, json.dumps([stack1, stack2, stack3, stack4]))
    monkeypatch.setattr('requests.get', mock_get)
    return mock_get


@pytest.fixture()
def mock_lizzy_post(monkeypatch):
    mock_post = MagicMock()
    stack1 = {'stack_name': 'stack1',
              'stack_version': '42',
              'description': 'stack1 (ImageVersion: 257)',
              'version': 'd42',
              'status': 'CREATE_COMPLETE',
              'creation_time': '2016-01-01T12:00:00Z'}
    mock_post.return_value = FakeResponse(200, json.dumps(stack1))
    monkeypatch.setattr('requests.post', mock_post)
    return mock_post


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


def test_fetch_token(mock_get_token):
    token = fetch_token('https://example.com', ['scope'], credentials_dir='/meta/credentials')

    assert token == '4CC3557OCC3N'

    mock_get_token.side_effect = InvalidCredentialsError('Error')

    with pytest.raises(SystemExit) as exc_info:  # type: py.code.ExceptionInfo
        fetch_token('https://example.com', ['scope'], credentials_dir='/meta/credentials')

    exception = exc_info.value
    assert repr(exception) == 'SystemExit(1,)'


def test_create(mock_get_token, mock_fake_lizzy, mock_lizzy_get, mock_lizzy_post):
    runner = CliRunner()
    runner = CliRunner()
    result = runner.invoke(main, ['create', config_path, '42', '1.0'],
                           env=FAKE_ENV, catch_exceptions=False)
    assert 'Fetching authentication token.. . OK' in result.output
    assert 'Requesting new stack.. OK' in result.output
    assert 'Stack ID: stack1-d42' in result.output
    assert 'Waiting for new stack... . . OK' in result.output
    assert 'Deployment Successful' in result.output
    assert 'kio version approve' not in result.output
    FakeLizzy.traffic.assert_called_once_with('stack1-d42', 100)
    FakeLizzy.delete.assert_not_called()
    FakeLizzy.reset()

    result = runner.invoke(main, ['create', config_path, '--keep-stacks', '0',
                                  '42', '1.0'],
                           env=FAKE_ENV, catch_exceptions=False)
    assert 'Fetching authentication token.. . OK' in result.output
    assert 'Requesting new stack.. OK' in result.output
    assert 'Stack ID: stack1-d42' in result.output
    assert 'Waiting for new stack... . . OK' in result.output
    assert 'Deployment Successful' in result.output
    assert 'kio version approve' not in result.output
    FakeLizzy.traffic.assert_called_once_with('stack1-d42', 100)
    assert FakeLizzy.delete.call_count == 2
    FakeLizzy.delete.assert_any_call('stack1-s7')
    FakeLizzy.delete.assert_any_call('stack1-s42')
    FakeLizzy.reset()

    # with explicit traffic
    result = runner.invoke(main, ['create', config_path, '42', '1.0', '--traffic', '42'],
                           env=FAKE_ENV, catch_exceptions=False)
    FakeLizzy.traffic.assert_called_once_with('stack1-d42', 42)
    FakeLizzy.reset()

    # with kio version approval
    result = runner.invoke(main, ['create', config_path, '43', '1.0', '-a', '42'], env=FAKE_ENV, catch_exceptions=False)
    assert 'kio version approve stack1 42' in result.output

    result = runner.invoke(main, ['create', '-v', config_path, '42', '1.0'],
                           env=FAKE_ENV, catch_exceptions=False)
    assert 'Fetching authentication token.. . OK' in result.output
    assert 'Requesting new stack.. OK' in result.output
    assert 'Stack ID: stack1-d42' in result.output
    assert 'Waiting for new stack...\n' in result.output
    assert 'CF:WAITING' in result.output
    assert 'CREATE_COMPLETE' in result.output
    assert 'Deployment Successful' in result.output

    FakeLizzy.final_state = 'ROLLBACK_COMPLETE'
    result = runner.invoke(main, ['create', '-v', config_path, '7', '1.0'], env=FAKE_ENV, catch_exceptions=False)
    assert 'Stack was rollback after deployment. Check your application log for possible reasons.' in result.output

    FakeLizzy.final_state = 'CF:CREATE_FAILED'
    result = runner.invoke(main, ['create', '-v', config_path, 'version', '1.0'], env=FAKE_ENV, catch_exceptions=False)
    assert 'Deployment failed: CF:CREATE_FAILED' in result.output

    FakeLizzy.reset()
    mock_lizzy_post.side_effect = requests.HTTPError(response=FakeResponse(404, '{"detail": "Not Found"}'))
    result = runner.invoke(main, ['create', '-v', config_path, 'version', '1.0'], env=FAKE_ENV, catch_exceptions=False)
    assert '[AGENT] Not Found' in result.output
    assert result.exit_code == 1


def test_delete(mock_get_token, mock_fake_lizzy):
    runner = CliRunner()
    result = runner.invoke(main, ['delete', 'lizzy-test', '1.0'], env=FAKE_ENV, catch_exceptions=False)
    assert 'Requesting stack deletion.. OK' in result.output


def test_traffic(mock_get_token, mock_fake_lizzy):
    runner = CliRunner()
    result = runner.invoke(main, ['traffic', 'lizzy-test', '1.0', '90'], env=FAKE_ENV, catch_exceptions=False)
    assert 'Requesting traffic change.. OK' in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ['version'], env=FAKE_ENV, catch_exceptions=False)
    for version_segment in (VERSION, MAJOR_VERSION, MINOR_VERSION):
        assert str(version_segment) in result.output


def test_list(mock_get_token, mock_lizzy_get):
    stack1 = {'stack_name': 'stack1',
              "description": "stack1 (ImageVersion: 257)",
              'version': 's1',
              'status': 'CREATE_COMPLETE',
              'creation_time': 1451649600.0}

    stack2 = {'stack_name': 'stack2',
              'version': 's2',
              "description": "stack1 (ImageVersion: 257)",
              'status': 'CF:TEST',
              'creation_time': 1448971200.0}

    stack3 = {'stack_name': 'stack1',
              'version': 's42',
              "description": "stack1 (ImageVersion: 257)",
              'status': 'CREATE_COMPLETE',
              'creation_time': 1448982000.0}

    stack4 = {'stack_name': 'stack1',
              "description": "stack1 (ImageVersion: 257)",
              'version': 's7',
              'status': 'CREATE_COMPLETE',
              'creation_time': 1451642400.0}

    runner = CliRunner()
    regular_list_result = runner.invoke(main, ['list', '-o', 'json'], env=FAKE_ENV, catch_exceptions=False)
    str_json = regular_list_result.output.splitlines()[-1]  # type: str
    regular_list = json.loads(str_json)  # type: list
    for stack in [stack1, stack2, stack3, stack4]:
        assert stack in regular_list

    runner = CliRunner()
    stack1_list_result = runner.invoke(main, ['list', '--all', '-o', 'json', 'stack1'], env=FAKE_ENV,
                                       catch_exceptions=False)
    str_json = stack1_list_result.output.splitlines()[-1]  # type: str
    stack1_list = json.loads(str_json)  # type: list
    assert stack1_list == [stack1, stack3, stack4]

    mock_lizzy_get.side_effect = requests.HTTPError(response=FakeResponse(404,
                                                                          '{"detail": "Detailed Error"}'))
    result = runner.invoke(main, ['list', '-o', 'json'], env=FAKE_ENV, catch_exceptions=False)
    assert '[AGENT] Detailed Error' in result.output
