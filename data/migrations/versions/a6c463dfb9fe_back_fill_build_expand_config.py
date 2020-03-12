"""
back fill build expand_config.

Revision ID: a6c463dfb9fe
Revises: b4df55dea4b3
Create Date: 2017-03-17 10:00:19.739858
"""

# revision identifiers, used by Alembic.
import json
import os

from app import app
from peewee import *
from data.database import BaseModel

revision = "a6c463dfb9fe"
down_revision = "b4df55dea4b3"


class RepositoryBuildTrigger(BaseModel):
    config = TextField(default="{}")


def upgrade(op, tables, tester):
    if not app.config.get("SETUP_COMPLETE", False):
        return

    repostioryBuildTriggers = RepositoryBuildTrigger.select()
    for repositoryBuildTrigger in repostioryBuildTriggers:
        config = json.loads(repositoryBuildTrigger.config)
        repositoryBuildTrigger.config = json.dumps(get_config_expand(config))
        repositoryBuildTrigger.save()


def downgrade(op, tables, tester):
    if not app.config.get("SETUP_COMPLETE", False):
        return

    repostioryBuildTriggers = RepositoryBuildTrigger.select()
    for repositoryBuildTrigger in repostioryBuildTriggers:
        config = json.loads(repositoryBuildTrigger.config)
        repositoryBuildTrigger.config = json.dumps(get_config_expand(config))
        repositoryBuildTrigger.save()


def create_context(current_subdir):
    if current_subdir == "":
        current_subdir = os.path.sep + current_subdir

    if current_subdir[len(current_subdir) - 1] != os.path.sep:
        current_subdir += os.path.sep

    context, _ = os.path.split(current_subdir)
    return context


def create_dockerfile_path(current_subdir):
    if current_subdir == "":
        current_subdir = os.path.sep + current_subdir

    if current_subdir[len(current_subdir) - 1] != os.path.sep:
        current_subdir += os.path.sep

    return current_subdir + "Dockerfile"


def get_config_expand(config):
    """
    A function to transform old records into new records.
    """
    if not config:
        return config

    # skip records that have been updated
    if "context" in config or "dockerfile_path" in config:
        return config

    config_expand = {}
    if "subdir" in config:
        config_expand = dict(config)
        config_expand["context"] = create_context(config["subdir"])
        config_expand["dockerfile_path"] = create_dockerfile_path(config["subdir"])

    return config_expand


def get_config_contract(config):
    """
    A function to delete context and dockerfile_path from config.
    """
    if not config:
        return config

    if "context" in config:
        del config["context"]

    if "dockerfile_path" in config:
        del config["dockerfile_path"]

    return config
