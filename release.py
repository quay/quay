import os


_GIT_HEAD_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "GIT_HEAD")

SERVICE = "quay"
GIT_HEAD = None
REGION = os.environ.get("QUAY_REGION")


# Load git head if available
if os.path.isfile(_GIT_HEAD_PATH):
    with open(_GIT_HEAD_PATH) as f:
        GIT_HEAD = f.read().strip()
