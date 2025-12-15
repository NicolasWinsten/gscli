import pytest
from typer.testing import CliRunner
from gscli.cli import app
import os

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def invoke_cli(runner):
    def _invoke(args, input=None):
        return runner.invoke(app, args, input=input)
    return _invoke

def test_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout

def test_submit_valid_file(invoke_cli):
    email = os.getenv("STUDENT2_EMAIL")
    password = os.getenv("STUDENT2_PASSWORD")
    course = os.getenv("COURSE_ID")
    assignment = os.getenv("CALCULATOR_ASSIGNMENT_ID")
    upload_file_path = "tests/uploads/calculator.py"

    print(f"Using email: {email}, course: {course}, assignment: {assignment}, upload_file_path: {upload_file_path}")
    result = invoke_cli([
        "submit",
        course,
        assignment,
        upload_file_path,
        "--leaderboard-name",
        "leaderboard-name"
    ], input=f"{email}\n{password}\n")

    assert result.exit_code == 0
    assert "Submission complete." in result.stdout
    assert "Autograder Results:" in result.stdout