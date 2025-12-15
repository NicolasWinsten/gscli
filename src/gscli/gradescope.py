

# GRADESCOPE_URL="https://www.gradescope.com"

# class TestCaseResult(NamedTuple):
#     passed: bool
#     name: str
#     output: str
#     score: float
#     max_score: float

# def report_test_case_results(result: TestCaseResult) -> None:
#     """Format and print test case result."""
#     color = "green" if result.passed else "red"
#     print(f"[{color}]{result.name} [bold]({result.score}/{result.max_score})[/bold]\n{result.output}[/{color}]")
    

# def submit_assigments(
#     session: requests.Session,
#     course_id: int,
#     assignment_id: int,
#     files: list[io.TextIOWrapper],
#     leaderboard_name: str | None = None,
#     wait_on_autograder: bool = False,
# ) -> None:
#     """Submit assignments to Gradescope."""
    
#     submission_link = upload_assignment(session, course_id, assignment_id, *files, leaderboard_name=leaderboard_name)

#     if submission_link is None:
#         raise Exception("Failed to submit. Probably the deadline has passed or you are missing a form field (e.g., leaderboard name).")

#     print("Submission complete.")

#     if not wait_on_autograder:
#         print(f"View your submission at: {submission_link}")
#         return

#     # Poll for submission results
#     timeout = 60
#     start_time = time.time()
#     poll_interval = 1
    
#     status_messages = {
#         'unprocessed': 'Waiting to be processed',
#         'autograder_harness_started': 'Preparing autograder',
#         'autograder_task_started': 'Autograder running',
#         'processed': 'Results ready'
#     }
    
#     spinner = Spinner("dots", text="Initializing...")
#     results_data = None
    
#     with Live(spinner, refresh_per_second=8):
#         while time.time() - start_time < timeout:
#             try:
#                 response = session.get(submission_link, headers={'Accept': 'application/json, text/javascript'})
#                 response.raise_for_status()
#                 json_response = response.json()
#                 # print(json.dumps(json_response, indent=4))

#             except Exception as e:
#                 print(f"Error fetching submission link: {e}")
#                 break
            
#             if json_response['status'] == 'processed':
#                 results_data = json_response['results']['tests']
#                 spinner.update(text="")
#                 break
#             else:
#                 status = json_response['status']
#                 status_text = status_messages[status]
#                 spinner.update(text=f"{status_text}...")
#                 time.sleep(poll_interval)
    
#     if results_data:
#         print("\nAutograder Results:")
#         print("=" * 50)
#         for result in results_data:
#             passed = result['status'] == 'passed'
#             test_case_result = TestCaseResult(
#                 passed=passed,
#                 name=result['name'],
#                 output=result['output'] or "",
#                 score=result['score'],
#                 max_score=result['max_score'],
#             )
#             report_test_case_results(test_case_result)
#     elif time.time() - start_time >= timeout:
#         print("\nTimeout reached while waiting for autograder results. Please check your submission later.")
#         print(f"View your submission at: {submission_link}")

        

