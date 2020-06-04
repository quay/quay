import logging

import psutil


logger = logging.getLogger(__name__)


def get_gunicorn_processes():
    """
    Return all gunicorn processes running within the current system or namespace.
    """
    return [p for p in psutil.process_iter() if p.name() == "gunicorn"]


def get_all_zombies():
    """
    Return all defunct (zombie) processes within the current system or namespace.
    """
    return [p for p in psutil.process_iter() if p.status() == "zombie"]
