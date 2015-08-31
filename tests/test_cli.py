from click.testing import CliRunner
from mock import MagicMock

from lizzy_client.cli import main


def test_not_enough_parameters(monkeypatch):
    mock_lizzy = MagicMock()
    monkeypatch.setattr('lizzy_client.cli.Lizzy', mock_lizzy)

    runner = CliRunner()
    result = runner.invoke(main, ['delete'])

    assert 'Error: Missing argument' in result.output
