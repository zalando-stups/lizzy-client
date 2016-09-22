import tempfile
from unittest.mock import MagicMock
from urllib.error import URLError

import pytest
from click.exceptions import UsageError
from lizzy_client.utils import (StackReference, get_stack_refs,
                                read_parameter_file)


@pytest.mark.parametrize(
    "input, expected_output",
    [
        (['foobar-stack'], [StackReference(name='foobar-stack', version=None)]),
        (['foobar-stack', '1'], [StackReference(name='foobar-stack', version='1')]),
        (['foobar-stack', '1', 'other-stack'],
         [StackReference(name='foobar-stack', version='1'), StackReference(name='other-stack', version=None)]),
        (['foobar-stack', 'v1', 'v2', 'v99', 'other-stack'],
         [StackReference(name='foobar-stack', version='v1'), StackReference(name='foobar-stack', version='v2'),
          StackReference(name='foobar-stack', version='v99'), StackReference(name='other-stack', version=None)]),
    ])
def test_get_stack_refs(input, expected_output):
    output = get_stack_refs(input)
    assert output == expected_output


def test_parameter_file():
    with tempfile.NamedTemporaryFile() as temporary_file:
        temporary_file.write(b"param1: value1\nparam2: value2")
        temporary_file.flush()
        parameters = read_parameter_file(temporary_file.name)
    assert sorted(parameters) == ['param1=value1', 'param2=value2']


def test_parameter_file_file_error(monkeypatch):
    monkeypatch.setattr("lizzy_client.utils.urlopen",
                        MagicMock(side_effect=URLError(0, "File not found")))
    with tempfile.NamedTemporaryFile() as temporary_file:
        temporary_file.write(b"param1: value1\nparam2: value2")
        temporary_file.flush()
        with pytest.raises(UsageError):
            read_parameter_file(temporary_file.name)


def test_parameter_file_yaml_error(monkeypatch):
    with tempfile.NamedTemporaryFile() as temporary_file:
        temporary_file.write(b"param1= value1\nparam2: value2")
        temporary_file.flush()
        with pytest.raises(UsageError):
            read_parameter_file(temporary_file.name)
