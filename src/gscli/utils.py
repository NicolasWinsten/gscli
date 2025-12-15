from typing import NamedTuple
import os
import requests
from gradescopeapi.classes.connection import GSConnection

def collect_file_objs(file_paths: list[str]) -> list:
	"""Open files and return a list of file objects."""
	file_paths = list(set(file_paths))  # remove duplicates

	opened_files = []
	try:
		for file_path in file_paths:
			opened_files.append(open(file_path, "rb"))
	except Exception as e:
		for f in opened_files:
			f.close()
		raise e
	return opened_files

def collect_files_in_directory(directory_path: str) -> list[str]:
	"""Collect all file paths in a directory."""
	file_paths = []
	for root, _, files in os.walk(directory_path):
		for file in files:
			file_paths.append(os.path.join(root, file))
	return file_paths

def login_gradescope(email: str, password: str) -> GSConnection:
	"""Login to Gradescope and return an authenticated session."""
	connection = GSConnection()
	try:
			connection.login(email, password)
	except Exception as e:
			print(f"Failed to login to Gradescope: [red]{e}[/red]")
			

	# TODO check for previous available session cookies to avoid re-login
	# TODO have user open browser to complete SSO/login if needed
	# TODO save cookies for future sessions

	# print(f"Logged in to Gradescope as {email}. Session cookies {connection.session.cookies.get_dict()}")

	return connection

class TestCaseResult(NamedTuple):
    passed: bool
    name: str
    output: str
    score: float
    max_score: float

def report_test_case_results(result: TestCaseResult) -> str:
    """Format and print test case result."""
    color = "green" if result.passed else "red"
    return f"[{color}]{result.name} [bold]({result.score}/{result.max_score})[/bold]\n{result.output}[/{color}]"

# TODO expand this to cover all possible grade result formats
def parse_results_json(json_data: dict) -> list[TestCaseResult]:
	"""Parse Gradescope results JSON into a list of TestCaseResult."""
	results = []
	for result in json_data['tests']:
		passed = result['status'] == 'passed'
		test_case_result = TestCaseResult(
			passed=passed,
			name=result['name'],
			output=result['output'] or "",
			score=result['score'],
			max_score=result['max_score'],
		)
		results.append(test_case_result)
	return results
