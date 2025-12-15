# gscli

A command-line tool for submitting assignments to Gradescope.

## Installation

```bash
pipx install .
```

Or for development:

Recommended to first create a virtual environment:
```bash
python3 -m venv path/to/virtual_environment`
source path/to/virtual_environment/bin/activate
```

```bash
pip install -e ".[dev]"
```

To exit the virtual environement:
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
