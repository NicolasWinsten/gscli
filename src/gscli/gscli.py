"""CLI commands."""
import sys
import time
from datetime import datetime, timezone
from rich import print
from rich.spinner import Spinner
from rich.live import Live
from gradescopeapi.classes.upload import upload_assignment
from pathlib import Path
import typer
from typing import List
from typing_extensions import Annotated
from questionary import Choice
import questionary
from .utils import (
  collect_file_objs, get_courses, write_to_current_assignment_file, report_test_case_results,
  login_gradescope, restore_connection, retrieve_current_assignment, store_session_cookies, parse_results_json,
  get_submissions, fetch_submission_status, make_submission_link,
  clear_session_cache, clear_current_assignment_file
)

# Global GSConnection connecting to Gradescope
connection = None

def print_err(e: Exception | str, color: bool = True) -> None:
    """Print an error message."""
    message = e.message if hasattr(e, 'message') else str(e)
    if color:
        print(f"[red]{message}[/red]", file=sys.stderr)
    else:
        print(message, file=sys.stderr)

# TODO add SSO option to login through institution through browser (or some other way through the command line?)
def login_if_needed() -> None:
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
            store_session_cookies(connection.session)
            print("[blue]Thank you! You are now logged in.[/blue]")
        except Exception as e:
            print_err(e)
            exit(1)

# TODO make this look nicer with course and assignment name
def report_current_assignment() -> None:
    """Report the user's currently set assignment."""
    current_assignment = retrieve_current_assignment()
    if current_assignment is None:
        print("[yellow]No current assignment found.[/yellow]")
        print("You can run [bold]gscli choose[/bold] to choose a course and assignment.")
        return
    
    course = current_assignment["course"]
    course_name = current_assignment["course_name"]
    assignment = current_assignment["assignment"]
    assignment_name = current_assignment["assignment_name"]
    print(f"You're working on {assignment_name} ({assignment}) for {course_name} ({course})")

def load_current_assignment_info_or_exit() -> dict:
    """Retrieve the course and assignment set by the user. If not set, remind user to set the current assignment and exit."""
    current_assignment = retrieve_current_assignment()
    if current_assignment is None:
        print("[yellow]No current assignment found.[/yellow]")
        print("Please run [bold]gscli choose[/bold] to choose a course and assignment.")
        exit(1)
    return current_assignment

def format_course(course_id: str, course_obj) -> str:
    """Format a course object from gradescopeapi into a string for display"""
    return f"{course_id} - {course_obj.name} ({course_obj.year} {course_obj.semester})"

def format_assignment(assignment_id: str, assignment_obj) -> str:
    """Format an assignment object from gradescopeapi into a string for display"""
    return f"{assignment_id} - {assignment_obj.name}"

def report_submission_results(list_of_results: list, submission_link: str) -> None:
    for result in list_of_results:
        print(report_test_case_results(result))
    print(f"[blue]View your submission at {submission_link}[/blue]")

def join(
    course: Annotated[int, typer.Argument(help="Course id")],
) -> None:
    """Join a course."""
    pass

    # store_session_cookies(connection.session)

def logout() -> None:
    """Log out of Gradescope"""
    clear_session_cache()
    print("[blue]You are logged out.[/blue]")

def clean() -> None:
    """Unset the current assignment and session cache.
    This will log you out and forget the current Gradescope assignment."""
    clear_session_cache()
    clear_current_assignment_file()
    print("[blue]Cleaned session cache and forgot current assignment.[/blue]")

# Scrape submission results for an assignment at submission link
# Currently, no easy way to do this besides scraping the assignment page for a
# submission link, and then collecting the results from there.
def status(
    course: Annotated[str | None, typer.Argument(help="Course id")] = None,
    assignment: Annotated[str | None, typer.Argument(help="Assignment id")] = None,
) -> None:
    """Check submission status for your assignment."""
    login_if_needed()
    if course is None or assignment is None:
        current_assignment = load_current_assignment_info_or_exit()
        course = current_assignment["course"]
        assignment = current_assignment["assignment"]

    try:
        assignment_submissions = get_submissions(connection.session, course_id=course)

        if assignment in assignment_submissions:
            submission_id = assignment_submissions[assignment]
            submission_link = make_submission_link(course, assignment, submission_id)
            status_json = fetch_submission_status(connection.session, submission_link)
        else:
            print_err(f"No submission found for assignment {assignment} in course {course}")
            return

    except Exception as e:
        print_err(e)
        print_err("Check that the course and assignment IDs are correct", color=False)
        return
    
    finally:
        store_session_cookies(connection.session)
        
    if status_json['status'] == 'processed':
        test_case_results = parse_results_json(status_json['results'])
        report_submission_results(test_case_results, submission_link)
    else:
        print(f"Status: {status_json['status']}")

# TODO clean up this function
# TODO prevent rich's automatic coloring cuz it looks bad
def list_assignments_and_courses(
    all: Annotated[bool, typer.Option("-a", "--all", help="Show all assignments (not just active ones)")] = False,
    show_only_courses: Annotated[bool, typer.Option("-c", "--courses", help="Only list courses")] = False
) -> None:
    """List courses and assignments."""
    login_if_needed()
    
    try:
        course_list = get_courses(connection)
    except Exception as e:
        print_err(e)
        return
    
    for id, course in course_list.items():
        print(format_course(id, course))
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
    course: Annotated[str | None, typer.Option("-c", "--course", help="Course id")] = None,
    assignment: Annotated[str | None, typer.Option("-a", "--assignment", help="Assignment id")] = None,
    files: Annotated[List[str] | None, typer.Argument(help="File list or directory to submit")] = None,
    leaderboard_name: Annotated[str | None, typer.Option("-n", "--leaderboard", help="Leaderboard name")] = None,
    recursive: Annotated[bool, typer.Option("-r", "--recursive", help="Recursively search directories for files")] = False,
) -> None:
    """Make a submission to your current assignment."""

    login_if_needed()
    if course is None or assignment is None:
        current_assignment = load_current_assignment_info_or_exit()
        course = current_assignment["course"] if course is None else course
        assignment = current_assignment["assignment"] if assignment is None else assignment

    # if no files are given, submit all files in current directory
    files = [str(Path.cwd().absolute())] if files is None else files

    # User can specify a directory to submit all files within
    try:
        files = collect_file_objs(files, recursive=recursive)
    except Exception as e:
        print_err(e)
        return

    # TODO prompt user to confirm submission details if the file list is long (and provide flag to skip -force)
    
    session = connection.session

    try:
        submission_link = upload_assignment(session, course, assignment, *files, leaderboard_name=leaderboard_name)
    except Exception as e:
        # a command like this: gscli submit 34 34 will cause an internal runtime error in gradescopeapi library
        # some course ids but not others cause a runtime error in that library
        # just report the course id was maybe wrong
        submission_link = None
    
    print("[gold1]Files uploaded:[/gold1]")
    for f in files:
        print(f" - {Path(f.name)}")
        f.close()

    if submission_link is None:
        print_err("[red]Failed to submit.[/red] Here are some possible reasons:", color=False)
        print_err(" - The course or assignment id is incorrect", color=False)
        print_err(" - The assignment/course is not accepting submissions", color=False)
        print_err(" - You are missing a required form field (e.g., leaderboard name)", color=False)
        return
    
    # Poll for submission results
    timeout = 100  # seconds
    start_time = time.time()
    poll_interval = 1
    
    # TODO lift this code out so that gscli status can also use it
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
                status_json = fetch_submission_status(session, submission_link)

            except Exception as e:
                print_err(e)
                break
        
            finally:
                store_session_cookies(session)
            
            if status_json['status'] == 'processed':
                results_data = parse_results_json(status_json['results'])
                break

            elif time.time() - start_time >= timeout:
                break

            status = status_json['status']
            status_text = status_messages.get(status, status)
            spinner.update(text=f"{status_text}...")
            time.sleep(poll_interval)

    if results_data:
        print("\nAutograder Results:")
        print("=" * 50)
        report_submission_results(results_data, submission_link)
    elif time.time() - start_time >= timeout:
        print("[red]Timeout reached while waiting for autograder results.[/red]")
        print(f"Check your submission at: [blue]{submission_link}[/blue]")
        print("Or use [bold]gscli status[/bold] command later to check for results.")


def choose() -> None:
    """Choose a course and assignment for the current working directory. Provide no arguments to interactively select a course and assignment."""
    
    login_if_needed()
    
    # Get course list
    try:
        course_list = get_courses(connection)
    except Exception as e:
        print_err(e)
        return
    
    if not course_list:
        print_err("No courses found", color=False)
        return
    
    # Prompt user to select one of their courses
    course_choices = [
        Choice(title=format_course(course_id, course_obj), value=course_id)
        for course_id, course_obj in course_list.items()
    ]

    if not course_choices:
        print_err("You're not enrolled in any courses.", color=False)
        return
    
    # Interactive course selection
    course_prompt = questionary.select(
        "Select a course:",
        choices=course_choices,
        use_arrow_keys=True,
        use_shortcuts=False
    )

    while True:
        selected_course_id = course_prompt.ask()
        if selected_course_id is None:
            print("[yellow]Cancelled.[/yellow]")
            return 
    
        try:
            assignments = list(connection.account.get_assignments(course_id=selected_course_id))
        except Exception as e:
            print_err(e)
            return
    
        if not assignments:
            print("No assignments found for this course")
            to_continue = typer.confirm("Select a different course?", default=True)
            if to_continue:
                continue
            else:
                return
        break
    
    # Prompt user to select one of the assignments from selected course
    assignment_choices = [
        Choice(title=format_assignment(a.assignment_id, a), value=a.assignment_id)
        for a in assignments if a.assignment_id
    ]
    
    selected_assignment_id = questionary.select(
        "Select an assignment:",
        choices=assignment_choices,
        use_arrow_keys=True,
        use_shortcuts=False
    ).ask()
    
    if selected_assignment_id is None:
        print("[yellow]Cancelled.[/yellow]")
        return
    
    # Initialize local config
    course_name = course_list[selected_course_id].name
    assignment_name = [a.name for a in assignments if a.assignment_id == selected_assignment_id][0]
    write_to_current_assignment_file(course_name, selected_course_id, assignment_name, selected_assignment_id)
    report_current_assignment()
    store_session_cookies(connection.session)
