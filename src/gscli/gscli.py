"""CLI commands."""
import io
import requests
import time
import json
from typing import NamedTuple
from rich import print
from rich.spinner import Spinner
from rich.live import Live
from gradescopeapi.classes.connection import GSConnection
from gradescopeapi.classes.upload import upload_assignment
import os
import typer
from typing import List
from typing_extensions import Annotated
from .utils import collect_files_in_directory, collect_file_objs, report_test_case_results, login_gradescope, parse_results_json

def join(
    course: Annotated[int, typer.Argument(help="Course id")],
) -> None:
    """Join a course."""
    print(f"Joining course {course}.")

def submit(
    course: Annotated[int, typer.Argument(help="Course id")],
    assignment: Annotated[int, typer.Argument(help="Assignment id")],
    files: Annotated[List[str] | None, typer.Argument(help="File list or directory to submit")] = None,
    leaderboard_name: Annotated[str | None, typer.Option(help="Leaderboard name")] = None,
) -> None:
    """Submit an assignment."""

    # if no files are given, submit all files in current directory
    files = ["."] if files is None else files

    # User can specify a directory to submit all files within
    # TODO catch errors and report
    if len(files) == 1 and os.path.isdir(files[0]):
        files = collect_file_objs(collect_files_in_directory(files[0]))
    else:
        files = collect_file_objs(files)

    # TODO prompt user to confirm submission details (and provide flag to skip -force)
    # if get_session() is None:

    # TODO check for cookies first to avoid re-login
    email = typer.prompt("Gradescope Email", hide_input=False)
    password = typer.prompt("Gradescope Password", hide_input=True)


    connection = login_gradescope(email, password)
    session = connection.session

    # remove duplicates from files
    submission_link = upload_assignment(session, course, assignment, *files, leaderboard_name=leaderboard_name)

    if submission_link is None:
        print("[red]Failed to submit. Probably the deadline has passed or you are missing a form field (e.g., leaderboard name).[/red]")
        return
    
    print("[amber]Submission complete.[/amber]")

    # Poll for submission results
    timeout = 60
    start_time = time.time()
    poll_interval = 1
    
    status_messages = {
        'unprocessed': 'Waiting to be processed',
        'autograder_harness_started': 'Preparing autograder',
        'autograder_task_started': 'Autograder running',
        'processed': 'Results ready'
    }
    
    spinner = Spinner("dots", text="Initializing...")
    results_data = None
    
    with Live(spinner, refresh_per_second=8):
        while time.time() - start_time < timeout:
            try:
                response = session.get(submission_link, headers={'Accept': 'application/json, text/javascript'})
                response.raise_for_status()
                json_response = response.json()

            except Exception as e:
                print(f"Error fetching submission link: {e}")
                break
            
            if json_response['status'] == 'processed':
                results_data = parse_results_json(json_response['results'])
                spinner.update(text="")
                break
            else:
                status = json_response['status']
                status_text = status_messages[status]
                spinner.update(text=f"{status_text}...")
                time.sleep(poll_interval)
    
    if results_data:
        print("\nAutograder Results:")
        print("=" * 50)
        for result in results_data:
            print(report_test_case_results(result))
    elif time.time() - start_time >= timeout:
        print("\nTimeout reached while waiting for autograder results. Please check your submission later.")
        print(f"View your submission at: [blue]{submission_link}[/blue]")
