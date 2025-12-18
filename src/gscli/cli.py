"""CLI application entry point."""

import typer

from .gscli import submit, join, status, logout, list_assignments_and_courses


app = typer.Typer(
    name="gscli",
    help="Gradescope CLI tool for submitting assignments and more.",
    # Disable showing local variables in exceptions, because it may reveal password
    pretty_exceptions_show_locals=False,
    no_args_is_help=True,
)

app.command(no_args_is_help=True)(submit)
app.command(no_args_is_help=True)(join)
app.command(name="list")(list_assignments_and_courses)
app.command(no_args_is_help=True)(status)
app.command()(logout)

if __name__ == "__main__":
    app()

