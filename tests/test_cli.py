import json
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest
import requests
from click import UsageError
from click.testing import CliRunner
from lizzy_client.cli import fetch_token, main, parse_stack_refs
from lizzy_client.lizzy import Lizzy
from lizzy_client.version import MAJOR_VERSION, MINOR_VERSION, VERSION
from tokens import InvalidCredentialsError
from urlpath import URL

fixtures_dir = Path(__file__).parent / 'fixtures'
config_path = str(fixtures_dir / 'test_config.yaml')

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
        self.headers = {'X-Lizzy-Output': 'Output'}

    def json(self):
        return json.loads(self.content)


class FakeLizzy(Lizzy):
    final_state = 'CREATE_COMPLETE'
    raise_exception = False
    traffic = MagicMock()
    delete = MagicMock()

    def __init__(self, base_url: str, access_token: str):
        self.access_token = "TOKEN"
        self.api_url = URL('https://localhost')

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
    result = runner.invoke(main, ['create', config_path, '42', '1.0'],
                           env=FAKE_ENV, catch_exceptions=False)
    assert 'Fetching authentication token.. . OK' in result.output
    assert 'Requesting new stack.. OK' in result.output
    assert 'Stack ID: stack1-d42' in result.output
    assert 'Waiting for new stack... . . OK' in result.output
    assert 'Deployment Successful' in result.output
    assert 'kio version approve' not in result.output
    FakeLizzy.traffic.assert_called_once_with('stack1-d42', 0)
    FakeLizzy.delete.assert_not_called()
    FakeLizzy.reset()

    result = runner.invoke(main, ['create', config_path,
                                  '--keep-stacks', '0',
                                  '--traffic', '100',
                                  '42', '1.0'],
                           env=FAKE_ENV, catch_exceptions=False)
    assert 'Fetching authentication token.. . OK' in result.output
    assert 'Requesting new stack.. OK' in result.output
    assert 'Stack ID: stack1-d42' in result.output
    assert 'Waiting for new stack... . . OK' in result.output
    assert 'Deployment Successful' in result.output
    assert 'kio version approve' not in result.output
    FakeLizzy.traffic.assert_called_once_with('stack1-d42', 100)
    assert FakeLizzy.delete.call_count == 3  # filter of stacks is done in the server-side
    FakeLizzy.delete.assert_any_call('stack1-s7')
    FakeLizzy.delete.assert_any_call('stack1-s42')
    FakeLizzy.reset()

    # with explicit traffic
    result = runner.invoke(main, ['create', config_path, '42', '1.0', '--traffic', '42'],
                           env=FAKE_ENV, catch_exceptions=False)
    FakeLizzy.traffic.assert_called_once_with('stack1-d42', 42)
    FakeLizzy.reset()

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


@pytest.mark.parametrize(
    "stack_name, stack_version, region, dry_run",
    [
        ("stack_id", "1", 'eu-central-1', False),
        ("574CC", "42", 'eu-central-1', True),
        ("stack_id", "7", 'eu-west-1', False),
        ("574CC", "2", 'eu-west-1', True),
    ])
def test_delete(mock_get_token, mock_fake_lizzy,
                stack_name, stack_version, region, dry_run):
    runner = CliRunner()
    dry_run_flag = ['--dry-run'] if dry_run else []
    result = runner.invoke(main,
                           ['delete']
                           + ['--region', region]
                           + dry_run_flag
                           + [stack_name, stack_version],
                           env=FAKE_ENV, catch_exceptions=False)
    assert "Requesting stack '{}-{}' deletion.. OK".format(stack_name, stack_version) in result.output
    stack_id = "{}-{}".format(stack_name, stack_version)
    mock_fake_lizzy.delete.assert_called_once_with(stack_id, dry_run=dry_run, region=region)


@pytest.mark.parametrize(
    "stack_refs, region, dry_run, expected_calls",
    [
        (["stack_id", "1"], 'eu-central-1', False, 1),
        (['foobar-stack', 'v1', 'v2', 'v99'], 'eu-central-1', False, 3),
        (["stack_id", "1"], 'eu-central-1', True, 1),
        (['foobar-stack', 'v1', 'v2', 'v99'], 'eu-central-1', True, 3)
    ])
def test_delete_multiple(mock_get_token, mock_fake_lizzy,
                         stack_refs, region, dry_run, expected_calls):
    runner = CliRunner()
    dry_run_flag = ['--dry-run'] if dry_run else []
    runner.invoke(main,
                  ['delete']
                  + ['--region', region]
                  + dry_run_flag
                  + stack_refs,
                  env=FAKE_ENV, catch_exceptions=False)
    assert mock_fake_lizzy.delete.call_count == expected_calls


@pytest.mark.parametrize(
    "stack_refs, region, dry_run, expected_calls",
    [
        (["stack_id"], 'eu-central-1', False, 1),
        (['foobar-stack', '1', 'other-stack'], 'eu-central-1', False, 2),
    ])
def test_delete_multiple_force(mock_get_token, mock_fake_lizzy,
                               stack_refs, region, dry_run, expected_calls):
    runner = CliRunner()
    dry_run_flag = ['--dry-run'] if dry_run else []
    result = runner.invoke(main,
                           ['delete']
                           + ['--region', region]
                           + dry_run_flag
                           + stack_refs,
                           env=FAKE_ENV, catch_exceptions=True)
    assert 'Please use the "--force" flag if you really want to delete multiple stacks.' in result.output
    #
    result_force = runner.invoke(main,
                                 ['delete']
                                 + ['--region', region]
                                 + ['--force']
                                 + dry_run_flag
                                 + stack_refs,
                                 env=FAKE_ENV, catch_exceptions=True)

    assert ('Please use the "--force" flag if you really want to delete multiple stacks.'
            not in result_force.output)
    assert mock_fake_lizzy.delete.call_count == expected_calls


def test_traffic(mock_get_token, mock_fake_lizzy):
    # normal call to change traffic
    runner = CliRunner()
    result = runner.invoke(main, ['traffic', 'lizzy-test', 'v10', '90'], env=FAKE_ENV, catch_exceptions=False)
    assert 'Requesting traffic change.. OK' in result.output
    mock_fake_lizzy.traffic.assert_called_once_with('lizzy-test-v10', 90)
    FakeLizzy.reset()

    # check the traffic of instances
    with patch.object(mock_fake_lizzy, 'get_stacks', return_value=[
            {'stack_name': 'lizzy-test', 'version': 'v1'}]), patch.object(
                mock_fake_lizzy, 'get_traffic', return_value={'weight': 100}):
        runner = CliRunner()
        result = runner.invoke(main, ['traffic', 'lizzy-test'], env=FAKE_ENV,
                               catch_exceptions=False)
        assert 'Requesting traffic change.. OK' not in result.output
        assert 'Requesting traffic info.. OK' in result.output
        mock_fake_lizzy.traffic.assert_not_called()
        mock_fake_lizzy.get_traffic.assert_called_with('lizzy-test-v1')


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
    # latest call in the mock
    url_called = mock_lizzy_get.call_args[0][0]
    assert URL(url_called).query == ''

    runner = CliRunner()
    runner.invoke(main, ['list', '--all', '-o', 'json', 'stack1'], env=FAKE_ENV)
    # latest call in the mock
    url_called = mock_lizzy_get.call_args[0][0]
    assert URL(url_called).query == 'references=stack1'

    with tempfile.NamedTemporaryFile() as senza_file:
        senza_file.write(textwrap.dedent('''
        SenzaInfo:
          StackName: insiderstack
        ''').encode())
        senza_file.flush()

        runner = CliRunner()
        runner.invoke(main, ['list', senza_file.name, 'secstack'], env=FAKE_ENV)

    url_called = mock_lizzy_get.call_args[0][0]
    assert URL(url_called).query == 'references={}'.format(quote('insiderstack,secstack'))

    mock_lizzy_get.side_effect = requests.HTTPError(response=FakeResponse(404,
                                                                          '{"detail": "Detailed Error"}'))
    result = runner.invoke(main, ['list', '-o', 'json'], env=FAKE_ENV, catch_exceptions=False)
    assert '[AGENT] Detailed Error' in result.output


def test_parse_arguments():
    # no files as argument
    stack_names = parse_stack_refs(['foo', 'bar'])
    assert stack_names == ['foo', 'bar']

    # use senza definitions as arguments
    with tempfile.NamedTemporaryFile() as senza_file:
        senza_file.write(textwrap.dedent('''
        SenzaInfo:
          StackName: insidefile
        ''').encode())
        senza_file.flush()

        stack_names = parse_stack_refs(['foobar', senza_file.name])
        assert stack_names == ['foobar', 'insidefile']

    # use invalid senza definition as arguments
    with tempfile.NamedTemporaryFile() as senza_file:
        senza_file.write(textwrap.dedent('''
        NotValid: impossible
        ''').encode())
        senza_file.flush()

        with pytest.raises(UsageError) as error:
            parse_stack_refs([senza_file.name])

        assert error.value.message.startswith('Invalid senza definition')

    # use not valid YAML file as input
    with tempfile.NamedTemporaryFile() as senza_file:
        senza_file.write('{{INVALID}}:file'.encode())
        senza_file.flush()

        with pytest.raises(UsageError) as error:
            parse_stack_refs([senza_file.name])

        assert error.value.message.startswith('Invalid senza definition')

    # use directory as input
    tmp_dir_path = tempfile.mkdtemp()
    assert tmp_dir_path in parse_stack_refs([tmp_dir_path])
