#!/usr/bin/env python3
"""Warn about API v1 discovery metadata omissions without importing Quay.

Audit explicitly declared GET, POST, PUT, PATCH, and DELETE handlers on @resource
classes for a single @nickname with a non-empty literal operation ID or a list
of distinct non-empty IDs. Missing nicknames silently omit operations from
/api/v1/discovery, including with ?internal=true. Unverifiable custom inherited
handlers receive a reminder to check their metadata manually.

Inspect non-test Python files under endpoints/api, including internal and
feature-gated resources. Filename arguments restrict reported findings; no
arguments audits all eligible files. This static audit does not establish
runtime visibility or check cross-handler ID collisions or route-count/cardinality
constraints; runtime discovery tests cover those for enabled routes.

Findings and inspection failures are advisory: the entry point reports warnings
and exits zero. This hook must not block commits or require a running Quay stack.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path


def escape(value, property_value=False):
    """Escape workflow command data and optional annotation properties."""
    value = str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def warn(path, line, message, *, root, selected):
    """Report a selected finding and return one, or zero when it is excluded."""
    if path not in selected:
        return 0
    filename = str(path.relative_to(root))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(
            f"::warning file={escape(filename, True)},line={line},"
            f"title=API discovery reminder::{escape(message)}"
        )
    else:
        print(f"WARNING {filename}:{line}: {message}")
    return 1


def main():
    """Audit selected API files, or all API files when no filenames are given."""
    try:
        root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        ).resolve()
    except (OSError, subprocess.CalledProcessError):
        root = Path.cwd()
    api_dir = root / "endpoints" / "api"
    http_methods = {"get", "post", "put", "patch", "delete"}
    files = sorted(
        path
        for path in api_dir.rglob("*.py")
        if not {"test", "tests"}.intersection(path.relative_to(api_dir).parts)
        and not path.name.startswith("test_")
    )
    requested = {(root / filename).resolve() for filename in sys.argv[1:]}
    selected = set(files).intersection(requested) if requested else set(files)

    reminders = 0

    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as error:
            reminders += warn(
                path,
                getattr(error, "lineno", None) or 1,
                f"Could not inspect annotations: {error}",
                root=root,
                selected=selected,
            )
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

        for resource in ast.walk(tree):
            if not isinstance(resource, ast.ClassDef):
                continue
            routes = [d for d in resource.decorator_list if decorator_name(d) == "resource"]
            if not routes:
                continue
            custom_bases = [
                ast.unparse(base)
                for base in resource.bases
                if decorator_name(base) not in {"ApiResource", "RepositoryParamResource"}
            ]
            if custom_bases:
                reminders += warn(
                    path,
                    resource.lineno,
                    f"{resource.name} inherits from {', '.join(custom_bases)}; inherited HTTP "
                    "handlers cannot be verified statically. Check their @nickname(...) metadata.",
                    root=root,
                    selected=selected,
                )
            for handler in resource.body:
                if not isinstance(handler, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if handler.name not in http_methods:
                    continue
                label = f"{resource.name}.{handler.name}"
                nicknames = [d for d in handler.decorator_list if decorator_name(d) == "nickname"]
                if not nicknames:
                    reminders += warn(
                        path,
                        handler.lineno,
                        f"{label} is missing @nickname(...); its {handler.name.upper()} operation "
                        "will be omitted from /api/v1/discovery, including with ?internal=true.",
                        root=root,
                        selected=selected,
                    )
                    continue
                if len(nicknames) != 1:
                    reminders += warn(
                        path,
                        handler.lineno,
                        f"{label} has multiple @nickname annotations; use one.",
                        root=root,
                        selected=selected,
                    )
                    continue
                nickname = nicknames[0]
                try:
                    if not isinstance(nickname, ast.Call):
                        raise ValueError("nickname must be called")
                    value_node = (
                        nickname.args[0]
                        if nickname.args
                        else next(
                            keyword.value for keyword in nickname.keywords if keyword.arg == "value"
                        )
                    )
                    value = ast.literal_eval(value_node)
                except (ValueError, TypeError, StopIteration):
                    reminders += warn(
                        path,
                        handler.lineno,
                        f"{label}: could not verify @nickname(...); use a non-empty literal "
                        "operation ID or a list of distinct IDs for multiple routes.",
                        root=root,
                        selected=selected,
                    )
                    continue
                values = value if isinstance(value, list) else [value]
                if (
                    not values
                    or any(not isinstance(item, str) or not item.strip() for item in values)
                    or len(set(values)) != len(values)
                ):
                    reminders += warn(
                        path,
                        handler.lineno,
                        f"{label}: @nickname(...) needs a non-empty string or list of distinct "
                        "non-empty strings.",
                        root=root,
                        selected=selected,
                    )
                    continue
    print(
        f"API discovery reminder: checked {len(selected)} file(s), {reminders} reminder(s). "
        "Advisory only; annotations do not change the hook exit status."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "WARNING: API discovery annotation check could not complete; continuing without blocking."
        )
    sys.exit(0)
