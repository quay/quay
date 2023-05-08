from data.logs_model import logs_model
from flask import request


def log_action(kind, user_or_orgname, metadata=None, repo=None, repo_name=None, performer=None):
    if not metadata:
        metadata = {}

    logs_model.log_action(
        kind,
        user_or_orgname,
        repository=repo,
        performer=performer,
        ip=request.remote_addr or None,
        metadata=metadata,
    )
