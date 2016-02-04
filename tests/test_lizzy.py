from unittest.mock import MagicMock
from requests import Response
import json
import os

from lizzy_client.lizzy import make_header, Lizzy


class FakeResponse(Response):
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: ste
        """
        self.status_code = status_code
        self._content = text
        self.raise_for_status = MagicMock()
        self.headers = {}

    def json(self):
        return json.loads(self.content)


def test_make_header():
    header = make_header('7E5770K3N')
    assert header['Authorization'] == 'Bearer 7E5770K3N'
    assert header['Content-type'] == 'application/json'


def test_properties():
    assert str(Lizzy('https://lizzy.example', '7E5770K3N').stacks_url) == 'https://lizzy.example/stacks'
    assert str(Lizzy('https://lizzy-2.example', '7E5770K3N').stacks_url) == 'https://lizzy-2.example/stacks'


def test_delete(monkeypatch):
    mock_delete = MagicMock()
    monkeypatch.setattr('requests.delete', mock_delete)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.delete('574CC')

    header = make_header('7E5770K3N')
    mock_delete.assert_called_once_with('https://lizzy.example/stacks/574CC', headers=header, verify=False)


def test_get_stack(monkeypatch):
    mock_get = MagicMock()
    mock_get.return_value = FakeResponse(200, '{"stack":"fake"}')
    monkeypatch.setattr('requests.get', mock_get)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    stack = lizzy.get_stack('574CC')

    header = make_header('7E5770K3N')
    mock_get.assert_called_once_with('https://lizzy.example/stacks/574CC', None, headers=header, verify=False)

    assert stack['stack'] == 'fake'


def test_get_stacks(monkeypatch):
    mock_get = MagicMock()
    mock_get.return_value = FakeResponse(200, '["stack1","stack2"]')
    monkeypatch.setattr('requests.get', mock_get)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    stacks = lizzy.get_stacks()

    header = make_header('7E5770K3N')
    mock_get.assert_called_once_with('https://lizzy.example/stacks', None, headers=header, verify=False)

    assert stacks == ["stack1", "stack2"]


def test_traffic(monkeypatch):
    mock_patch = MagicMock()
    mock_patch.return_value = FakeResponse(200, '["stack1","stack2"]')
    monkeypatch.setattr('requests.patch', mock_patch)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    lizzy.traffic('574CC', 42)

    header = make_header('7E5770K3N')
    mock_patch.assert_called_once_with('https://lizzy.example/stacks/574CC', headers=header, data='{"new_traffic": 42}',
                                       verify=False)


def test_new_stack(monkeypatch):
    test_dir = os.path.dirname(__file__)
    yaml_path = os.path.join(test_dir, 'test_config.yaml')  # we can use any file for this test
    with open(yaml_path) as yaml_file:
        senza_yaml = yaml_file.read()

    mock_post = MagicMock()
    mock_post.return_value = FakeResponse(200, '{"stack_id":"574CC1D"}')
    monkeypatch.setattr('requests.post', mock_post)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    stack_id = lizzy.new_stack('10', 2, 42, yaml_path, None, [])

    header = make_header('7E5770K3N')
    data = {'image_version': "10",
            'keep_stacks': 2,
            'new_traffic': 42,
            'parameters': [],
            'senza_yaml': senza_yaml}
    mock_post.assert_called_once_with('https://lizzy.example/stacks', headers=header,
                                      data=json.dumps(data),
                                      json=None,
                                      verify=False)

    assert stack_id == "574CC1D"

    mock_post.reset_mock()
    data_with_ver = {'image_version': "10",
                     'keep_stacks': 2,
                     'new_traffic': 42,
                     'parameters': [],
                     'senza_yaml': senza_yaml,
                     "application_version": "420", }
    lizzy.new_stack('10', 2, 42, yaml_path, "420", [])
    mock_post.assert_called_once_with('https://lizzy.example/stacks', headers=header,
                                      data=json.dumps(data_with_ver),
                                      json=None,
                                      verify=False)

    mock_post.reset_mock()
    data_with_params = {'image_version': "10",
                        'keep_stacks': 2,
                        'new_traffic': 42,
                        'parameters': ['abc', 'def'],
                        'senza_yaml': senza_yaml,
                        "application_version": "420", }
    lizzy.new_stack('10', 2, 42, yaml_path, "420", ['abc', 'def'])
    mock_post.assert_called_once_with('https://lizzy.example/stacks', headers=header,
                                      data=json.dumps(data_with_params),
                                      json=None,
                                      verify=False)


def test_wait_for_deployment(monkeypatch):
    monkeypatch.setattr('time.sleep', MagicMock())
    mock_get_stack = MagicMock()
    mock_get_stack.side_effect = [{'status': 'CF:SOME_STATE'}, {'status': 'CF:SOME_STATE'},
                                  {'status': 'CF:SOME_OTHER_STATE'}, {'status': 'CF:CREATE_COMPLETE'}]
    monkeypatch.setattr('lizzy_client.lizzy.Lizzy.get_stack', mock_get_stack)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    states = list(lizzy.wait_for_deployment('574CC1D'))

    assert states == ['CF:SOME_STATE', 'CF:SOME_STATE', 'CF:SOME_OTHER_STATE', 'CF:CREATE_COMPLETE']

    mock_get_stack.reset_mock()
    mock_get_stack.side_effect = [{'wrong_key': 'CF:SOME_STATE'}, {'wrong_key': 'CF:SOME_STATE'},
                                  {'wrong_key': 'CF:SOME_STATE'}]
    states = list(lizzy.wait_for_deployment('574CC1D'))
    assert states == ["Failed to get stack (2 retries left): KeyError('status',).",
                      "Failed to get stack (1 retries left): KeyError('status',).",
                      "Failed to get stack (0 retries left): KeyError('status',).", ]
