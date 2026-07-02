import json
import os
import tempfile

DEFAULT_BOOTSTRAP_TOKEN_PATH = "/var/lib/quay/quay-machine-token.json"
MAX_BOOTSTRAP_TOKEN_FILE_BYTES = 4096


def _access_token_from_json(token_json):
    try:
        data = json.loads(token_json)
    except (TypeError, ValueError):
        return None

    access_token = data.get("access_token") if isinstance(data, dict) else None
    return access_token if isinstance(access_token, str) and access_token else None


def read_token_file(path):
    """Read an access token from path, returning None if it is missing or malformed."""
    try:
        with open(path, encoding="utf-8") as f:
            token_json = f.read(MAX_BOOTSTRAP_TOKEN_FILE_BYTES + 1)
    except (OSError, UnicodeDecodeError):
        return None

    if len(token_json) > MAX_BOOTSTRAP_TOKEN_FILE_BYTES:
        return None

    return _access_token_from_json(token_json)


def delete_token_file(path):
    """Delete path if present, returning whether a file was removed.

    Missing files are expected in multi-node installations where bootstrap token
    files are node-local. Raises OSError for failures other than absence.
    """
    try:
        os.unlink(path)
    except FileNotFoundError:
        return False

    return True


def write_token_file(path, access_token):
    """Write {"access_token": "..."} to path with 0600 permissions.

    Creates parent directories if they don't exist and uses atomic replacement to
    prevent partial writes. Raises OSError on failure.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, mode=0o700, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent or None, suffix=".tmp")
        content = json.dumps({"access_token": access_token})
        os.write(fd, content.encode("utf-8"))
        os.fchmod(fd, 0o600)
        os.close(fd)
        fd = None
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def read_bootstrap_token(app_config):
    """Read the configured local bootstrap token, returning None if absent or malformed."""
    token_path = app_config.get("BOOTSTRAP_TOKEN_PATH", DEFAULT_BOOTSTRAP_TOKEN_PATH)
    return read_token_file(token_path)


def write_bootstrap_token(app_config, access_token):
    """Write the configured local bootstrap token.

    Raises OSError on failure so callers can roll back database token state.
    """
    token_path = app_config.get("BOOTSTRAP_TOKEN_PATH", DEFAULT_BOOTSTRAP_TOKEN_PATH)
    write_token_file(token_path, access_token)


def delete_bootstrap_token(app_config):
    """Delete the configured local bootstrap token if present.

    Returns whether a file was removed. Missing files are not an error because
    token files are node-local in multi-node installations.
    """
    token_path = app_config.get("BOOTSTRAP_TOKEN_PATH", DEFAULT_BOOTSTRAP_TOKEN_PATH)
    return delete_token_file(token_path)
