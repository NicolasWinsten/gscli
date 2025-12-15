import pytest
from typer.testing import CliRunner
from gscli.cli import app

@pytest.fixture
def runner():
    return CliRunner()

def test_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout

