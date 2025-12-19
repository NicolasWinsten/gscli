"""CLI application entry point."""

import typer

from .gscli import report_current_assignment, submit, join, status, logout, choose, clean, list_assignments_and_courses


app = typer.Typer(
    name="gscli",
    help="Gradescope CLI tool for submitting assignments and more.",
    # Disable showing local variables in exceptions, because it may reveal password
    pretty_exceptions_show_locals=False,
    # no_args_is_help=True,
)

app.command()(choose)
app.command(no_args_is_help=True)(submit)
app.command(no_args_is_help=True)(join)
app.command(name="list")(list_assignments_and_courses)
app.command()(status)
app.command()(logout)
app.command()(clean)
# if __name__ == "__main__":
#     app()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Default action when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        report_current_assignment()
        print("Run gscli --help on how to submit your assignment or choose a different assignment.")
