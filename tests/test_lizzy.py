from mock import MagicMock
from requests import Response
import json

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

    def json(self):
        return json.loads(self.content)


def test_make_header():
    header = make_header('7E5770K3N')
    assert header['Authorization'] == 'Bearer 7E5770K3N'
    assert header['Content-type'] == 'application/json'


def test_properties():
    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    assert lizzy.stacks_url == 'https://lizzy.example/stacks'


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
    mock_get.assert_called_once_with('https://lizzy.example/stacks/574CC', headers=header, verify=False)

    assert stack['stack'] == 'fake'


def test_get_stacks(monkeypatch):
    mock_get = MagicMock()
    mock_get.return_value = FakeResponse(200, '["stack1","stack2"]')
    monkeypatch.setattr('requests.get', mock_get)

    lizzy = Lizzy('https://lizzy.example', '7E5770K3N')
    stacks = lizzy.get_stacks()

    header = make_header('7E5770K3N')
    mock_get.assert_called_once_with('https://lizzy.example/stacks', headers=header, verify=False)

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
