"""CLI application entry point."""

import typer

from .gscli import submit, join


app = typer.Typer(
    name="gscli",
    help="Gradescope CLI tool for submitting assignments and more.",
)

app.command()(submit)
app.command()(join)

if __name__ == "__main__":
    app()

