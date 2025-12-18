from multiprocessing import connection
import sys
from typing import NamedTuple
import os
import json
import requests
from pathlib import Path
from cryptography.fernet import Fernet
import platformdirs
from gradescopeapi.classes.connection import GSConnection
from gradescopeapi.classes.account import Account

# Encrypted cache directory - use platform-appropriate paths
CONFIG_DIR = Path(platformdirs.user_config_dir("gscli"))
CACHE_FILE = CONFIG_DIR / "session_cache"
KEY_FILE = CONFIG_DIR / "cache.key"

# TODO can use encryption to store cookies,
# but better to use keyring when this code is moved to intermediate server

# def _get_or_create_key() -> bytes:
# 	"""Get or create the encryption key for cache."""
# 	if KEY_FILE.exists():
# 		return KEY_FILE.read_bytes()
# 	
# 	# Create config directory if it doesn't exist
# 	CONFIG_DIR.mkdir(parents=True, exist_ok=True)
# 	
# 	# Generate new key
# 	key = Fernet.generate_key()
# 	KEY_FILE.write_bytes(key)
# 	# Restrict key file to user only (0o600 = rw------)
# 	KEY_FILE.chmod(0o600)
# 	
# 	return key

# def _get_cipher() -> Fernet:
# 	"""Get Fernet cipher for encryption/decryption."""
# 	key = _get_or_create_key()
# 	return Fernet(key)

def _get_stored_session_cookies() -> dict | None:
	"""Retrieve session cookies from cache."""
	if not CACHE_FILE.exists():
		return None
	
	try:
		# TODO: Re-enable encryption when out of development
		# cipher = _get_cipher()
		# encrypted_data = CACHE_FILE.read_bytes()
		# decrypted_data = cipher.decrypt(encrypted_data)
		# cookies_json = decrypted_data.decode('utf-8')
		
		cookies_json = CACHE_FILE.read_text()
		cookies_dict = json.loads(cookies_json)
		return cookies_dict
	except Exception as e:
		print(
			f"WARNING: Cached session cookies could not be retrieved: {e}",
			flush=True,
			file=sys.stderr
		)
		return None
	

def store_session_cookies(session: requests.Session) -> None:
	"""Saves session cookies to ~/.config/gscli for future use."""
	CONFIG_DIR.mkdir(parents=True, exist_ok=True)
	cookies_dict = session.cookies.get_dict()
	cookies_json = json.dumps(cookies_dict)
	
	# TODO: Re-enable encryption when out of development
	# cipher = _get_cipher()
	# encrypted_data = cipher.encrypt(cookies_json.encode('utf-8'))
	# CACHE_FILE.write_bytes(encrypted_data)
	
	# Restrict cache file to user only (may fail silently on Windows, so wrap in try-except)
	try:
		CACHE_FILE.write_text(cookies_json)
		CACHE_FILE.chmod(0o600)
	except OSError as e:
		print(
			f"WARNING: Could not set file permissions on cache file: {e}",
			flush=True,
			file=sys.stderr
		)

def clear_session_cache() -> None:
	"""Clears the stored session cache."""
	if CACHE_FILE.exists():
		CACHE_FILE.unlink()

# Restore connection from cached session cookies
def restore_connection() -> GSConnection | None:
	"""Restore Gradescope connection from cached session if available."""
	
	cookies = _get_stored_session_cookies()
	if cookies is None:
		return None
	
	connection = GSConnection()
	connection.session.cookies.update(cookies)

	# try to retrieve courses to verify session validity
	response = connection.session.get(f"{connection.gradescope_base_url}/account")
	if response.status_code == 200:
		# pretty hacky since I'm doing what the library code should be doing
		# TODO If this causes issues, consider contributing a method to gradescopeapi
		# for restoring a session from stored cookies
		connection.account = Account(connection.session)
		connection.logged_in = True
		return connection
		
	# Clear the cache file if the session is invalid
	clear_session_cache()
	
	return None

def login_gradescope(email: str, password: str) -> GSConnection:
	"""Login to Gradescope and return an authenticated session."""
	connection = GSConnection()
	connection.login(email, password)
	
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


def collect_file_objs(file_paths: list[str], recursive: bool) -> list:
	"""Collect and open files in binary read mode.
	
	Args:
		file_paths: List of file or directory paths. Hidden files are only included if explicitly named.
		recursive: If True, recursively follow subdirectories
		
	Returns:
		List of file objects opened in binary read mode
	"""
	file_paths = list(set(file_paths))  # remove duplicates
	file_objs = []
	

	def should_skip(path: Path) -> bool:
		"""Check if a path should be skipped (hidden or in skip list)."""
		return path.name.startswith('.')
	
	def collect_from_dir(dir_path: Path, is_recursive: bool) -> None:
		"""Recursively collect files from a directory."""
		try:
			for item in dir_path.iterdir():
				if should_skip(item):
					continue
				if item.is_file():
					try:
						file_objs.append(open(item, "rb"))
					except (IOError, OSError) as e:
						print(f"WARNING: Could not open file {item}: {e}", file=sys.stderr)
				elif item.is_dir() and is_recursive:
					collect_from_dir(item, is_recursive=True)
		except (IOError, OSError) as e:
			print(f"WARNING: Could not access directory {dir_path}: {e}", file=sys.stderr)

	for path_str in file_paths:
		path = Path(path_str)
		try:
			if path.is_file():
				# Open explicitly named files regardless of hidden status
				file_objs.append(open(path, "rb"))
			elif path.is_dir():
				collect_from_dir(path, is_recursive=recursive)
		except (IOError, OSError) as e:
			print(f"WARNING: Could not access path {path}: {e}", file=sys.stderr)
			
	return file_objs


# def parse_assignments_list(json_data: dict) -> dict[int, str]:
# 	"""Parse assignments list from Gradescope JSON data."""
# 	assignments = {}
# 	for assignment in json_data.get('assignments', []):
# 		assignments[assignment['id']] = assignment['name']
# 	return assignments

