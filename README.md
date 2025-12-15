# gscli

A command-line tool built with Python and Typer.

## Installation

```bash
pipx install .
```

Or for development:

```bash
pip install -e ".[dev]"
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

Lint:
```bash
ruff check src/
```
