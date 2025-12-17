import pytest
from typer.testing import CliRunner
from gscli.cli import app
import os
from gscli.utils import clear_session_cache

from dotenv import load_dotenv

# Load environment variables from .env.test
load_dotenv(".env.test", override=True)

STUDENT_EMAIL_1     = os.getenv("STUDENT1_EMAIL")
STUDENT_PASSWORD_1  = os.getenv("STUDENT1_PASSWORD")

STUDENT_EMAIL_2 = os.getenv("STUDENT2_EMAIL")
STUDENT_PASSWORD_2 = os.getenv("STUDENT2_PASSWORD")

PYTHON_COURSE_ID="1197898"
PYTHON_ASSIGNMENT_1="7308477"
PYTHON_ASSIGNMENT_2="7324354"
CORRECT_CALCULATOR_FILE_PATH = "tests/uploads/correct/calculator.py"
INCORRECT_CALCULATOR_FILE_PATH = "tests/uploads/off_by_1/calculator.py"


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

def test_can_restore_session(invoke_cli):
    # clear any existing session cache
    clear_session_cache()

    # First, try to list courses. This should prompt for login.
    result = invoke_cli([
        "list",
    ], input=f"{STUDENT_EMAIL_1}\n{STUDENT_PASSWORD_1}\n")

    assert result.exit_code == 0
    assert "Please log in to Gradescope. Your credentials will not be saved anywhere." in result.stdout
    assert "Thank you! You are now logged in." in result.stdout

    # Now, try to submit again, which should restore the session
    result = invoke_cli([
        "list",
    ])

    assert result.exit_code == 0
    assert "Please log in to Gradescope. Your credentials will not be saved anywhere." not in result.stdout

    clear_session_cache()



def test_submit_valid_file(invoke_cli):
    clear_session_cache()

    result = invoke_cli([
        "submit",
        PYTHON_COURSE_ID,
        PYTHON_ASSIGNMENT_1,
        CORRECT_CALCULATOR_FILE_PATH,
        "--leaderboard-name",
        "leaderboard-name"
    ], input=f"{STUDENT_EMAIL_2}\n{STUDENT_PASSWORD_2}\n")

    assert result.exit_code == 0
    assert "Files uploaded:" in result.stdout
    assert CORRECT_CALCULATOR_FILE_PATH in result.stdout
    assert "Autograder Results:" in result.stdout

    clear_session_cache()

    # TODO check test cases

# def test_wrong_password(invoke_cli):
#     email = os.getenv("STUDENT2_EMAIL")
#     wrong_password = "wrong_password"
#     course = os.getenv("COURSE_ID")
#     assignment = os.getenv("CALCULATOR_ASSIGNMENT_ID")
#     upload_file_path = "tests/uploads/calculator.py"

#     result = invoke_cli([
#         "submit",
#         course,
#         assignment,
#         upload_file_path,
#         "--leaderboard-name",
#         "leaderboard-name"
#     ], input=f"{email}\n{wrong_password}\n")

#     assert result.exit_code != 0
#     assert "Invalid credentials" in result.stdout


# def test_assignment_unavailable(invoke_cli):
#     email = os.getenv("STUDENT2_EMAIL")
#     password = os.getenv("STUDENT2_PASSWORD")
#     course = os.getenv("COURSE_ID")
#     unavailable_assignment = "999999"  # Assuming this assignment ID does not exist
#     upload_file_path = "tests/uploads/calculator.py"

#     result = invoke_cli([
#         "submit",
#         course,
#         unavailable_assignment,
#         upload_file_path,
#         "--leaderboard-name",
#         "leaderboard-name"
#     ], input=f"{email}\n{password}\n")

#     assert result.exit_code != 0
#     assert "Assignment not found or not available for submission" in result.stdout