#!/usr/bin/env bash
# Advisory only: missing @nickname metadata makes discovery omit an operation.
# pre-commit passes changed filenames; no arguments audits all API v1 files.
# Keep this independent of Quay imports, feature flags, and running services.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "WARNING: API discovery annotation check skipped: python3 is unavailable."
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || REPO_ROOT="$PWD"

if ! python3 - "$REPO_ROOT" "$@" <<'PY'
import ast
import os
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1]).resolve()
api_dir = root / "endpoints" / "api"
http_methods = {"get", "post", "put", "patch", "delete"}
files = sorted(
    path for path in api_dir.rglob("*.py")
    if not {"test", "tests"}.intersection(path.relative_to(api_dir).parts)
    and not path.name.startswith("test_")
)
requested = {(root / filename).resolve() for filename in sys.argv[2:]}
selected = set(files).intersection(requested) if requested else set(files)

reminders = 0


def escape(value, property_value=False):
    """Escape workflow command data and optional annotation properties."""
    value = str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def warn(path, line, message):
    """Report advisory findings only for files selected by pre-commit."""
    global reminders
    if path not in selected:
        return
    reminders += 1
    filename = str(path.relative_to(root))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning file={escape(filename, True)},line={line},"
              f"title=API discovery reminder::{escape(message)}")
    else:
        print(f"WARNING {filename}:{line}: {message}")


operation_ids = defaultdict(list)
for path in files:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as error:
        warn(path, getattr(error, "lineno", None) or 1, f"Could not inspect annotations: {error}")
        continue

    aliases = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "endpoints.api":
            aliases.update({alias.asname or alias.name: alias.name for alias in node.names})

    def decorator_name(decorator):
        """Resolve decorator names, including aliases imported from endpoints.api."""
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            return aliases.get(target.id, target.id)
        if isinstance(target, ast.Attribute):
            return target.attr
        return None

    def route_count(decorators, method):
        """Count declared URLs for a method, or return None for dynamic routing."""
        count = 0
        for decorator in decorators:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                return None
            if any(isinstance(arg, ast.Starred) for arg in decorator.args):
                return None
            if any(keyword.arg is None for keyword in decorator.keywords):
                return None
            methods = next((keyword.value for keyword in decorator.keywords
                            if keyword.arg == "methods"), None)
            if methods is not None:
                try:
                    allowed = ast.literal_eval(methods)
                except (ValueError, TypeError):
                    return None
                if (not isinstance(allowed, (list, tuple, set))
                        or any(not isinstance(item, str) for item in allowed)):
                    return None
                if method.upper() not in {item.upper() for item in allowed}:
                    continue
            count += len(decorator.args)
        return count

    for resource in ast.walk(tree):
        if not isinstance(resource, ast.ClassDef):
            continue
        routes = [d for d in resource.decorator_list if decorator_name(d) == "resource"]
        if not routes:
            continue
        custom_bases = [ast.unparse(base) for base in resource.bases
                        if decorator_name(base) not in {"ApiResource", "RepositoryParamResource"}]
        if custom_bases:
            warn(path, resource.lineno,
                 f"{resource.name} inherits from {', '.join(custom_bases)}; inherited HTTP "
                 "handlers cannot be verified statically. Check their @nickname(...) metadata.")
        for handler in resource.body:
            if not isinstance(handler, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if handler.name not in http_methods:
                continue
            label = f"{resource.name}.{handler.name}"
            nicknames = [d for d in handler.decorator_list if decorator_name(d) == "nickname"]
            if not nicknames:
                warn(path, handler.lineno,
                     f"{label} is missing @nickname(...); its {handler.name.upper()} operation "
                     "will be omitted from /api/v1/discovery "
                     "(internal APIs require ?internal=true).")
                continue
            if len(nicknames) != 1:
                warn(path, handler.lineno, f"{label} has multiple @nickname annotations; use one.")
                continue
            nickname = nicknames[0]
            try:
                if not isinstance(nickname, ast.Call):
                    raise ValueError("nickname must be called")
                value_node = nickname.args[0] if nickname.args else next(
                    keyword.value for keyword in nickname.keywords if keyword.arg == "value"
                )
                value = ast.literal_eval(value_node)
            except (ValueError, TypeError, StopIteration):
                warn(path, handler.lineno,
                     f"{label}: could not verify @nickname(...); use a non-empty literal "
                     "operation ID or a list of distinct IDs for multiple routes.")
                continue
            values = value if isinstance(value, list) else [value]
            if (not values or any(not isinstance(item, str) or not item.strip() for item in values)
                    or len(set(values)) != len(values)):
                warn(path, handler.lineno,
                     f"{label}: @nickname(...) needs a non-empty string or list of distinct "
                     "non-empty strings.")
                continue
            count = route_count(routes, handler.name)
            if count is None:
                warn(path, handler.lineno,
                     f"{label}: could not determine the route count statically; verify that "
                     "@nickname(...) provides a distinct operation ID for every route.")
            elif len(values) < count:
                warn(path, handler.lineno,
                     f"{label} serves {count} routes but @nickname(...) provides only "
                     f"{len(values)} operation ID(s); discovery needs a distinct ID per route.")
                continue
            # Lists are alternative IDs allocated by discovery for multiple routes.
            # Only scalar/scalar collisions are unambiguous without running Quay.
            if isinstance(value, str):
                operation_ids[value].append((path, handler.lineno, label))

for operation_id, handlers in operation_ids.items():
    if len(handlers) > 1:
        locations = ", ".join(f"{path.relative_to(root)}:{line} ({label})"
                              for path, line, label in handlers)
        for path, line, label in handlers:
            warn(path, line, f"{label}: duplicate operation ID {operation_id!r}: {locations}. "
                 "Discovery operation IDs must be unique; review feature-gated alternatives.")

print(f"API discovery reminder: checked {len(selected)} file(s), {reminders} reminder(s). "
      "Advisory only; annotations do not change the hook exit status.")
PY
then
  echo "WARNING: API discovery annotation check could not complete; continuing without blocking."
fi

# Findings and checker errors must never block a commit or the pre-commit CI job.
exit 0
