# gscli

A command-line tool for submitting assignments to Gradescope.

## Installation

```bash
pipx install .
```

Or for development:

*Recommended to first create a virtual environment:*
```bash
python3 -m venv path/to/virtual_environment
source path/to/virtual_environment/bin/activate
```

```bash
pip install -e ".[dev]"
```

To exit the virtual environment:
```bash
deactivate
```

## Usage

```bash
gscli submit --help
```

## Development

Format code:
```bash
black src/
```

Run tests:
```bash
pytest
```

#### Note:
Tests require credentials for gradescope accounts stored in environment variables. Running tests will not work on your machine.

Lint:
```bash
ruff check src/
```

## Uninstall
```bash
pipx uninstall gscli
```

# TODO
1. ~~Submit assignments~~
2. Store authentication cookie, so user doesn't need to login frequently
3. Prompt user to sign in with SSO through their browser
4. Add command to join a course
5. Add command to retrieve scores of the last submission
6. Handle all grading results (not just autograder results)
