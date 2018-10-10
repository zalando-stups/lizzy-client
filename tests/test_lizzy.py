import json
from unittest.mock import MagicMock

import pytest
from lizzy_client.lizzy import Lizzy, make_header
from requests import Response


STACK1 = """{"creation_time": 1460635167,
              "description": "Lizzy Bus (ImageVersion: 257)",
              "stack_name": "lizzy-bus",
              "status": "CREATE_COMPLETE",
              "version": "257"}"""


class FakeResponse(Response):
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: str
        """
        self.status_code = status_code
        self._content = text
        self.raise_for_status = MagicMock()
        self.headers = {'X-Lizzy-Output': ''}

    def json(self):
        return json.loads(self.content)


def test_make_header():
    header = make_header('7E5770K3N')
    assert header['Authorization'] == 'Bearer 7E5770K3N'
    assert header['Content-type'] == 'application/json'


def test_properties():
    assert str(Lizzy('https://lizzy.example', '7E5770K3N').stacks_url) == 'https://lizzy.example/api/stacks'
    assert str(Lizzy('https://lizzy-2.example', '7E5770K3N').stacks_url) == 'https://lizzy-2.example/api/stacks'


@pytest.mark.parametrize(
    "stack_id, region, dry_run",
    [
        ("stack_id", 'eu-central-1', False),
        ("574CC", 'eu-central-1', True),
        ("stack_id", 'eu-west-1', False),
        ("574CC", 'eu-west-1', True),
    ])
def test_delete(monkeypatch, stack_id, region, dry_run):
    mock_delete = MagicMock()
    monkeypatch.setattr('requests.delete', mock_delete)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.delete(stack_id, region=region, dry_run=dry_run)

    header = make_header('7E5770K3N')
    url = 'https://lizzy.example/api/stacks/{}'.format(stack_id)
    expected_data = {"region": region, "dry_run": dry_run}
    mock_delete.assert_called_once_with(url,
                                        json=expected_data,
                                        headers=header,
                                        verify=False)


def test_get_stack(monkeypatch):
    mock_get = MagicMock()
    mock_get.return_value = FakeResponse(200, '{"stack":"fake"}')
    monkeypatch.setattr('requests.get', mock_get)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    stack = lizzy.get_stack('574CC')

    header = make_header('7E5770K3N')
    mock_get.assert_called_once_with('https://lizzy.example/api/stacks/574CC', None, headers=header, verify=False)

    assert stack['stack'] == 'fake'


def test_get_stacks(monkeypatch):
    mock_get = MagicMock()
    mock_get.return_value = FakeResponse(200, '["stack1","stack2"]')
    monkeypatch.setattr('requests.get', mock_get)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    stacks = lizzy.get_stacks()

    header = make_header('7E5770K3N')
    mock_get.assert_called_once_with('https://lizzy.example/api/stacks', None, headers=header, verify=False)

    assert stacks == ["stack1", "stack2"]


def test_traffic(monkeypatch):
    mock_patch = MagicMock()
    mock_patch.return_value = FakeResponse(200, '["stack1","stack2"]')
    monkeypatch.setattr('requests.patch', mock_patch)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.traffic('574CC', 42)

    header = make_header('7E5770K3N')
    mock_patch.assert_called_once_with('https://lizzy.example/api/stacks/574CC',
                                       headers=header,
                                       data=None,
                                       json={"new_traffic": 42},
                                       verify=False)

    # call with region payload
    mock_patch.reset_mock()
    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.traffic('574CC', 42, region='ab-foo-7')

    header = make_header('7E5770K3N')
    mock_patch.assert_called_once_with('https://lizzy.example/api/stacks/574CC',
                                       headers=header,
                                       data=None,
                                       json={'new_traffic': 42,
                                             'region': 'ab-foo-7'},
                                       verify=False)


def test_get_traffic(monkeypatch):
    mock_request = MagicMock()
    mock_request.return_value = FakeResponse(200, '{"weight": 100.0}')
    monkeypatch.setattr('requests.get', mock_request)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.get_traffic('lizzy-test')

    header = make_header('7E5770K3N')
    mock_request.assert_called_once_with(
        'https://lizzy.example/api/stacks/lizzy-test/traffic', None,
        headers=header, verify=False)

    mock_request.reset_mock()
    mock_request.return_value = FakeResponse(200, '["stack1","stack2"]')

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.get_traffic('574CC', region='ab-foo-7')

    header = make_header('7E5770K3N')
    url = 'https://lizzy.example/api/stacks/574CC/traffic?region=ab-foo-7'
    mock_request.assert_called_once_with(url, None, headers=header,
                                         verify=False)


def test_scale(monkeypatch):
    mock_patch = MagicMock()
    monkeypatch.setattr('requests.patch', mock_patch)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.scale('574CC', 3)

    header = make_header('7E5770K3N')
    mock_patch.assert_called_once_with('https://lizzy.example/api/stacks/574CC',
                                       headers=header,
                                       data=None,
                                       json={"new_scale": 3},
                                       verify=False)

    # call with region payload
    mock_patch.reset_mock()
    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.scale('574CC', 3, region='ab-foo-7')

    header = make_header('7E5770K3N')
    mock_patch.assert_called_once_with('https://lizzy.example/api/stacks/574CC',
                                       headers=header,
                                       data=None,
                                       json={'new_scale': 3,
                                             'region': 'ab-foo-7'},
                                       verify=False)


@pytest.mark.parametrize(
    "version, parameters, region, disable_rollback, dry_run, force, tags, keep_stacks, new_traffic",
    [
        ("new_version", ['10'], None, True, False, False, [], 2, 42),
        ("another_version", ['10'], "eu-central-1", False, True, False, [], 2,
         42),
        ("yet_another_version", [], None, False, False, True, [], 42, 7),
        ("43", ['abc', 'def'], None, True, False, True, ['tag1=value1'], 42, 7),
        ("newer_version", [], None, True, True, False, [], 2, 42),
    ])
def test_new_stack(monkeypatch,
                   version, parameters, region, disable_rollback, dry_run,
                   force, tags, keep_stacks, new_traffic):
    mock_post = MagicMock()
    mock_post.return_value = FakeResponse(200, STACK1)
    monkeypatch.setattr('requests.post', mock_post)
    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    stack, output = lizzy.new_stack(keep_stacks=keep_stacks,
                                    new_traffic=new_traffic,
                                    senza_yaml={'MyDefinition': 'Values'},
                                    stack_version=version,
                                    disable_rollback=disable_rollback,
                                    parameters=parameters,
                                    dry_run=dry_run,
                                    region=region,
                                    tags=tags)
    stack_name = stack['stack_name']
    assert stack_name == 'lizzy-bus'

    header = make_header('7E5770K3N')
    data = {'keep_stacks': keep_stacks,
            'new_traffic': new_traffic,
            'parameters': parameters,
            'disable_rollback': disable_rollback,
            'dry_run': dry_run,
            'senza_yaml': "{MyDefinition: Values}\n",
            'stack_version': version,
            'tags': tags}

    # only pass region when it is not None
    if region:
        data['region'] = region

    mock_post.assert_called_once_with('https://lizzy.example/api/stacks',
                                      headers=header,
                                      json=data,
                                      data=None,
                                      verify=False)


def test_wait_for_deployment(monkeypatch):
    monkeypatch.setattr('time.sleep', MagicMock())
    mock_get_stack = MagicMock()
    mock_get_stack.side_effect = [{'status': 'CF:SOME_STATE'}, {'status': 'CF:SOME_STATE'},
                                  {'status': 'CF:SOME_OTHER_STATE'}, {'status': 'CREATE_COMPLETE'}]
    monkeypatch.setattr('lizzy_client.lizzy.Lizzy.get_stack', mock_get_stack)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    states = list(lizzy.wait_for_deployment('574CC1D'))

    assert states == ['CF:SOME_STATE', 'CF:SOME_STATE', 'CF:SOME_OTHER_STATE', 'CREATE_COMPLETE']

    mock_get_stack.reset_mock()
    mock_get_stack.side_effect = [{'wrong_key': 'CF:SOME_STATE'}, {'wrong_key': 'CF:SOME_STATE'},
                                  {'wrong_key': 'CF:SOME_STATE'}]
    states = list(lizzy.wait_for_deployment('574CC1D'))
    assert states == ["Failed to get stack (2 retries left): KeyError('status',).",
                      "Failed to get stack (1 retries left): KeyError('status',).",
                      "Failed to get stack (0 retries left): KeyError('status',).", ]
