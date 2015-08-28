import pytest
import os.path

from lizzy_client.configuration import Parameters, ConfigurationError


@pytest.fixture
def parameters_empty():
    # parameters with a file that doesn't exist
    parameters = Parameters('None')
    return parameters


@pytest.fixture
def parameters_complete_with_file():
    test_dir = os.path.dirname(__file__)
    path = os.path.join(test_dir, 'test_config.yaml')
    parameters = Parameters(path)
    return parameters


@pytest.fixture
def parameters_complete_with_file_and_args():
    test_dir = os.path.dirname(__file__)
    path = os.path.join(test_dir, 'test_config.yaml')
    parameters = Parameters(path, user='arg_user')
    return parameters


@pytest.fixture
def parameters_complete_with_args():
    # parameters with a file that doesn't exist
    parameters = Parameters('None', user='user', password='password', lizzy_url='lizzy-url', token_url='token-url')
    return parameters


def test_validation(parameters_empty, parameters_complete_with_args):
    with pytest.raises(ConfigurationError) as exc_info:  # type: py.code.ExceptionInfo
        parameters_empty.validate()

    exception = exc_info.value
    assert str(exception) == 'Error: Missing option "--user".'

    parameters_complete_with_args.validate()


def test_parameter_access(parameters_complete_with_args, parameters_complete_with_file,
                          parameters_complete_with_file_and_args):
    assert parameters_complete_with_args.user == 'user'
    assert parameters_complete_with_args.lizzy_url == 'lizzy-url'

    assert parameters_complete_with_file.user == 'file_user'
    assert parameters_complete_with_file.lizzy_url == 'https://lizzy.example/api'

    # arguments override config
    assert parameters_complete_with_file_and_args.user == 'arg_user'
    assert parameters_complete_with_file_and_args.lizzy_url == 'https://lizzy.example/api'


def test_parsing_error():
    test_dir = os.path.dirname(__file__)
    path = os.path.join(test_dir, 'test_invalid_config.yaml')

    with pytest.raises(ConfigurationError) as exc_info:  # type: py.code.ExceptionInfo
        Parameters(path)

    exception = exc_info.value
    assert str(exception) == 'Error parsing YAML file.'
