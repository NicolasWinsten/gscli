"""CLI application entry point."""

import typer

from .gscli import submit, join, list_assignments_and_courses, auth_callback


app = typer.Typer(
    name="gscli",
    help="Gradescope CLI tool for submitting assignments and more.",
    # Disable showing local variables in exceptions, because it may reveal password
    pretty_exceptions_show_locals=False,
    no_args_is_help=True,
    callback=auth_callback
)

app.command()(submit)
app.command()(join)
app.command(name="list")(list_assignments_and_courses)

if __name__ == "__main__":
    app()

