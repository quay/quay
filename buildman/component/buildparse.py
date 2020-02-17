import re


def extract_current_step(current_status_string):
    """
    Attempts to extract the current step numeric identifier from the given status string.

    Returns the step number or None if none.
    """
    # Older format: `Step 12 :`
    # Newer format: `Step 4/13 :`
    step_increment = re.search(r"Step ([0-9]+)/([0-9]+) :", current_status_string)
    if step_increment:
        return int(step_increment.group(1))

    step_increment = re.search(r"Step ([0-9]+) :", current_status_string)
    if step_increment:
        return int(step_increment.group(1))
