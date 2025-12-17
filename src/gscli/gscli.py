"""CLI commands."""
import time
from datetime import datetime, timezone
from rich import print
from rich.spinner import Spinner
from rich.live import Live
from gradescopeapi.classes.upload import upload_assignment
import os
import typer
from typing import List
from typing_extensions import Annotated
from .utils import (
  collect_files_in_directory, collect_file_objs, report_test_case_results,
  login_gradescope, restore_connection, store_session_cookies,
  parse_results_json
)

# Global GSConnection connecting to Gradescope
connection = None

def print_err(e: Exception | str) -> None:
    """Print an error message."""
    if hasattr(e, 'message'):
        print(f"[red]{e.message}[/red]")
    else:
        print(f"[red]{e}[/red]")

# Callback to authenticate user before running any command
def auth_callback() -> None:
    global connection
    connection = restore_connection()
    if connection is not None:
        print("[blue]Restored previous session.[/blue]")
    else:
        print("[yellow]Please log in to Gradescope. Your credentials will not be saved anywhere.[/yellow]")
        print("[yellow]gscli only saves session cookies.[/yellow]")
        email = typer.prompt("Gradescope Email", hide_input=False)
        password = typer.prompt("Gradescope Password", hide_input=True)
        try:
            connection = login_gradescope(email, password)
            print("[blue]Thank you! You are now logged in.[/blue]")
        except Exception as e:
            print_err(e)
            exit(1)


def join(
    course: Annotated[int, typer.Argument(help="Course id")],
) -> None:
    """Join a course."""
    pass

    # store_session_cookies(connection.session)

# Scrape submission results for an assignment at submission link
# Currently, no easy way to do this besides scraping the assignment page for a
# submission link, and then collecting the results from there.
def status(
    course: Annotated[int, typer.Argument(help="Course id")],
    assignment: Annotated[int, typer.Argument(help="Assignment id")],
) -> None:
    """Check submission status for an assignment."""
    pass

    # store_session_cookies(connection.session)

def list_assignments_and_courses(
    all: Annotated[bool, typer.Option("-a", "--all", help="Show all assignments (not just active ones)")] = False,
    show_only_courses: Annotated[bool, typer.Option("-c", "--courses", help="Only list courses")] = False
) -> None:
    """List courses and assignments."""
    try:
        courses = connection.account.get_courses()
    except Exception as e:
        print_err(e)
        return
    
    course_list = { **courses['student'], **courses['instructor'] }

    for id, course in course_list.items():
        print(f"[bold]{id} - {course.name}[/bold] - {course.year} {course.semester}")
        if show_only_courses:
            continue

        try:
            assignments = list(connection.account.get_assignments(course_id=id))
        except Exception as e:
            print_err(e)
            return

        if assignments:
            # Calculate max widths for alignment
            max_id_width = max(len(str(a.assignment_id)) for a in assignments)
            max_name_width = max(len(a.name) for a in assignments)
            
            now = datetime.now(timezone.utc)
            
            # Sort assignments: due today first, then active, then late, then others
            def due_today(a):
                return a.due_date and a.due_date.date() == now.date()
            
            def active(a):
                return a.release_date and a.due_date and (a.release_date <= now <= a.due_date)
            
            def late(a):
                return a.late_due_date and (now <= a.late_due_date) and (not a.due_date or now > a.due_date)

            sorted_assignments = sorted(assignments, key=lambda a: (not due_today(a), not active(a), not late(a)))
            
            # Filter assignments if not showing all
            if not all:
                sorted_assignments = [a for a in sorted_assignments if active(a) or late(a)]
            
            for a in sorted_assignments:
                # Build assignment info string with alignment
                due_str = "today" if due_today(a) else (a.due_date.strftime("%m/%d") if a.due_date else "N/A")
                grade_str = f" [{a.grade}/{a.max_grade}]" if a.grade and a.max_grade else ""
                
                # Check if late submissions are accepted
                late_str = ""
                if a.late_due_date and now <= a.late_due_date and (not a.due_date or now > a.due_date):
                    late_str = " (Accepting late submissions)"
                
                # Calculate time remaining for assignments due today
                # TODO don't display time remaining if past due date
                time_remaining_str = ""
                if due_today(a):
                    time_delta = a.due_date - now
                    hours_left = time_delta.total_seconds() / 3600
                    if hours_left < 1:
                        minutes_left = int(time_delta.total_seconds() / 60)
                        time_remaining_str = f" ({minutes_left} min left)"
                    else:
                        hours_left = int(hours_left)
                        time_remaining_str = f" ({hours_left} hr{'s' if hours_left != 1 else ''} left)"
                
                # Format the assignment line with proper spacing
                assignment_line = f" - {str(a.assignment_id).ljust(max_id_width)} {a.name.ljust(max_name_width)} (Due: {due_str}){grade_str}{late_str}{time_remaining_str}"
                
                # Color assignments: yellow for due today, green for active, default for others
                if due_today(a):
                    print(f"[yellow]{assignment_line}[/yellow]")
                elif active(a):
                    print(f"[green]{assignment_line}[/green]")
                else:
                    print(assignment_line)

    store_session_cookies(connection.session)

def submit(
    course: Annotated[str, typer.Argument(help="Course id")],
    assignment: Annotated[str, typer.Argument(help="Assignment id")],
    files: Annotated[List[str] | None, typer.Argument(help="File list or directory to submit")] = None,
    leaderboard_name: Annotated[str | None, typer.Option(help="Leaderboard name")] = None,
) -> None:
    """Submit an assignment"""

    # if no files are given, submit all files in current directory
    files = ["."] if files is None else files

    # User can specify a directory to submit all files within
    try:
        if len(files) == 1 and os.path.isdir(files[0]):
            files = collect_file_objs(collect_files_in_directory(files[0]))
        else:
            files = collect_file_objs(files)
    except Exception as e:
        print_err(e)
        return

    # TODO prompt user to confirm submission details if the file list is long (and provide flag to skip -force)
    
    session = connection.session

    try:
        submission_link = upload_assignment(session, course, assignment, *files, leaderboard_name=leaderboard_name)
    except Exception as e:
        # TODO a command like this: gscli submit 1198 74777 ./tests/uploads/correct/calculator.py
        # causes an ugly runtime error in the gradescopeapi library
        submission_link = None

    if submission_link is None:
        print("[red]Failed to submit.[/red] Here are some possible reasons:")
        print(" - The course or assignment id is incorrect")
        print(" - The assignment/course is not accepting submissions")
        print(" - You are missing a required form field (e.g., leaderboard name)")
        return
    
    print("[gold1]Files uploaded:[/gold1]")
    for f in files:
        print(f" - {f.name}")
        f.close()

    # Poll for submission results
    timeout = 100  # seconds
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
    
    # TODO don't use context manager here. It's confusing
    with Live(spinner, refresh_per_second=8, transient=True):
        while True:
            try:
                response = session.get(submission_link, headers={'Accept': 'application/json, text/javascript'})
                response.raise_for_status()
                json_response = response.json()

            except Exception as e:
                print_err(e)
                break
            
            if json_response['status'] == 'processed':
                results_data = parse_results_json(json_response['results'])
                break

            if time.time() - start_time >= timeout:
                break

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
        print("[red]Timeout reached while waiting for autograder results.[/red]")
        print(f"Check your submission at: [blue]{submission_link}[/blue]")
        print("Or use [bold]gscli status[/bold] command later to check for results.")

    store_session_cookies(connection.session)
