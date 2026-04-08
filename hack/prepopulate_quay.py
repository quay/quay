"""
Usage
  python3 hack/prepopulate_quay.py [options]

Description
  Prepopulates a Quay database with organizations, repositories, and tags.
  Connects to the DB used by the Quay app by overriding the application's
  DB configuration via QUAY_OVERRIDE_CONFIG before importing `app`.

Key options
  --db-uri            Database URI to target. Defaults to
                      postgresql://quay:quay@localhost:5432/quay
  --orgs              Number of orgs to create (default: 1)
  --repos             Number of repos per org (default: 1)
  --tags              Number of tags per repo (default: 1)
  --org-prefix        Prefix for org names (default: org)
  --repo-prefix       Prefix for repo names (default: repo)
  --tag-prefix        Prefix for tag names (default: v)
  --public-repos      Make all created repos public
  --admin-username    Bootstrap admin username (default: user1)
  --admin-password    Bootstrap admin password (default: password)
  --admin-email       Bootstrap admin email (default: user1@example.com)
  --location          ImageStorageLocation to use (default: local_us)

Examples
  # Populate default external DB with 1 org, 1 repo, and 1 tag
  python3 hack/prepopulate_quay.py

  # Populate a local Postgres on host port 5432
  python3 hack/prepopulate_quay.py --orgs 2 --repos 3 --tags 1 \
    --db-uri postgresql://quay:quay@localhost:5432/quay

  # Create public repos and custom prefixes
  python3 hack/prepopulate_quay.py --orgs 1 --repos 2 --tags 2 \
    --public-repos --org-prefix demoorg --repo-prefix images --tag-prefix r

Requirements
  - Run with the same Python environment used by the Quay app (install requirements.txt)
  - The database must be reachable from where you run this script
  - The configured ImageStorageLocation exists (script will create it if missing)

Common issues
  - ModuleNotFoundError (e.g., authlib): ensure you run with the Quay virtualenv
  - Connection errors: verify --db-uri host/port and network reachability
  - Permission errors: ensure provided DB user has rights to insert rows
"""

#!/usr/bin/env python3
import argparse
import json
import logging
import os
from datetime import datetime

from data import model
from data.database import ImageStorageLocation, Repository, User
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from digest.digest_tools import sha256_digest
from image.docker.schema1 import DockerSchema1ManifestBuilder

LOG = logging.getLogger(__name__)
TEMP_BLOB_EXPIRATION_SEC = 120


def ensure_location(name: str = "local_us"):
    try:
        return ImageStorageLocation.get(ImageStorageLocation.name == name)
    except ImageStorageLocation.DoesNotExist:
        LOG.warning("ImageStorageLocation '%s' not found; creating it", name)
        return ImageStorageLocation.create(name=name)


def ensure_user(username: str, password: str, email: str) -> User:
    try:
        user = User.get(User.username == username)
        return user
    except User.DoesNotExist:
        user = model.user.create_user(username, password, email)
        # Use update to satisfy typing and avoid direct field assignment warnings
        User.update(verified=True).where(User.id == user.id).execute()
        return User.get(User.id == user.id)


def create_org(name: str, email: str, creating_user: User) -> User:
    try:
        return model.organization.get_organization(name)
    except model.organization.InvalidOrganizationException:
        return model.organization.create_organization(name, email, creating_user)


def _populate_blob(repo: Repository, content: bytes, location: ImageStorageLocation):
    digest = str(sha256_digest(content))
    model.blob.store_blob_record_and_temp_link_in_repo(
        repo, digest, location, len(content), TEMP_BLOB_EXPIRATION_SEC
    )
    return digest


def create_tag(repo: Repository, tag_name: str, location: ImageStorageLocation, storage):
    # Create a tiny single-layer schema1 manifest and tag it
    ns = repo.namespace_user.username
    builder = DockerSchema1ManifestBuilder(ns, repo.name, "")

    layer_content = f"layer-{datetime.utcnow().timestamp()}".encode("utf-8")
    digest = _populate_blob(repo, layer_content, location)
    builder.insert_layer(digest, json.dumps({"id": "layer-1", "Size": len(layer_content)}))

    manifest = builder.clone(tag_name).build()
    repo_ref = RepositoryReference.for_repo_obj(repo)

    created_tag, _ = registry_model.create_manifest_and_retarget_tag(
        repo_ref, manifest, tag_name, storage, raise_on_error=True
    )

    return created_tag


def create_repo(namespace: str, name: str, creating_user: User, public: bool) -> Repository:
    repo = model.repository.get_repository(namespace, name)
    if repo is None:
        repo = model.repository.create_repository(namespace, name, creating_user)
        if repo is None:
            # Another process might have created it concurrently; fetch again
            repo = model.repository.get_repository(namespace, name)
        if repo is None:
            raise RuntimeError(f"Failed to create or fetch repository {namespace}/{name}")
        if public:
            model.repository.set_repository_visibility(repo, "public")
    return repo


def main():
    parser = argparse.ArgumentParser(
        description="Prepopulate Quay with organizations, repositories, and tags"
    )
    parser.add_argument("--orgs", type=int, default=1, help="Number of organizations to create")
    parser.add_argument(
        "--repos", type=int, default=1, help="Repositories per organization to create"
    )
    parser.add_argument("--tags", type=int, default=1, help="Tags per repository to create")
    parser.add_argument("--org-prefix", default="org", help="Prefix for organization names")
    parser.add_argument("--repo-prefix", default="repo", help="Prefix for repository names")
    parser.add_argument("--tag-prefix", default="v", help="Prefix for tag names")
    parser.add_argument("--public-repos", action="store_true", help="Create repositories as public")
    parser.add_argument("--admin-username", default="user1", help="Admin username")
    parser.add_argument("--admin-password", default="password", help="Admin password")
    parser.add_argument("--admin-email", default="user1@example.com", help="Admin email")
    parser.add_argument(
        "--location", default="local_us", help="ImageStorageLocation name to use for blobs"
    )
    parser.add_argument(
        "--db-uri",
        default="postgresql://quay:quay@localhost:5432/quay",
        help="Database URI to target (overrides app DB_URI)",
    )

    args = parser.parse_args()

    # Inject DB override before importing app so the DB driver targets the external instance
    override_env = os.environ.get("QUAY_OVERRIDE_CONFIG")
    if override_env:
        try:
            current = json.loads(override_env)
        except json.JSONDecodeError:
            current = {}
        current["DB_URI"] = args.db_uri
        os.environ["QUAY_OVERRIDE_CONFIG"] = json.dumps(current)
    else:
        os.environ["QUAY_OVERRIDE_CONFIG"] = json.dumps({"DB_URI": args.db_uri})

    # Import the app after setting overrides so configuration picks them up
    from app import app
    from app import storage as app_storage  # noqa: WPS433 (runtime import by design)

    log_level = os.environ.get("LOGGING_LEVEL", getattr(logging, app.config["LOGGING_LEVEL"]))
    logging.basicConfig(level=log_level)

    admin_user = ensure_user(args.admin_username, args.admin_password, args.admin_email)
    location = ensure_location(args.location)

    created_summary = {"organizations": [], "repositories": 0, "tags": 0}

    for oi in range(1, args.orgs + 1):
        org_name = f"{args.org_prefix}{oi}"
        org_email = f"{org_name}@example.com"
        org = create_org(org_name, org_email, admin_user)
        created_summary["organizations"].append(org.username)

        for ri in range(1, args.repos + 1):
            repo_name = f"{args.repo_prefix}{ri}"
            repo = create_repo(org.username, repo_name, admin_user, args.public_repos)
            created_summary["repositories"] += 1

            for ti in range(1, args.tags + 1):
                tag_name = f"{args.tag_prefix}{ti}"
                create_tag(repo, tag_name, location, app_storage)
                created_summary["tags"] += 1

    LOG.info(
        "Created %d orgs, %d repos, %d tags",
        len(created_summary["organizations"]),
        created_summary["repositories"],
        created_summary["tags"],
    )
    print(json.dumps(created_summary, indent=2))


if __name__ == "__main__":
    main()
