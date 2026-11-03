"""Exercise the advisory shell hook without importing or starting Quay."""

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "check-api-discovery.sh"


class TestAPIDiscoveryReminder(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="quay-discovery-hook-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.api = self.root / "endpoints" / "api"
        self.api.mkdir(parents=True)

    def write(self, name, source):
        path = self.api / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return str(path.relative_to(self.root))

    def run_hook(self, *filenames, environment=None):
        env = dict(os.environ, GITHUB_ACTIONS="false")
        env.update(environment or {})
        result = subprocess.run(
            ["/bin/bash", str(HOOK), *filenames],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_missing_nickname_warns_without_blocking(self):
        filename = self.write(
            "example.py",
            """\
            @resource("/v1/example")
            class Example(ApiResource):
                def get(self):
                    pass
            """,
        )
        output = self.run_hook(filename)
        self.assertIn("WARNING endpoints/api/example.py:3", output)
        self.assertIn("Example.get is missing @nickname", output)
        self.assertIn("1 reminder(s)", output)

    def test_valid_aliases_and_multi_route_nicknames(self):
        filename = self.write(
            "example.py",
            """\
            from endpoints.api import nickname as operation, resource as route

            @route("/v1/one", "/v1/two")
            class Example(ApiResource):
                @operation(["getOne", "getTwo"])
                def get(self):
                    pass

                @operation("createExample")
                def post(self):
                    pass

                def options(self):
                    pass

                def head(self):
                    pass
            """,
        )
        self.assertIn("0 reminder(s)", self.run_hook(filename))

    def test_empty_or_invalid_nicknames_warn(self):
        for value in ['""', '"  "', "[]", '["same", "same"]', "[123]", "None"]:
            with self.subTest(value=value):
                filename = self.write(
                    "example.py",
                    f"""\
                    @resource("/v1/example")
                    class Example(ApiResource):
                        @nickname({value})
                        def get(self):
                            pass
                    """,
                )
                self.assertIn("needs a non-empty", self.run_hook(filename))

    def test_duplicate_ids_use_unchanged_files_as_context(self):
        source = """\
            @resource("/v1/example")
            class Example(ApiResource):
                @nickname("getExample")
                def get(self):
                    pass
            """
        changed = self.write("changed.py", source)
        self.write("unchanged.py", source)
        output = self.run_hook(changed)
        self.assertIn("WARNING endpoints/api/changed.py", output)
        self.assertNotIn("WARNING endpoints/api/unchanged.py", output)
        self.assertIn("duplicate operation ID 'getExample'", output)

    def test_internal_and_disabled_features_are_checked(self):
        filename = self.write(
            "example.py",
            """\
            @resource("/v1/example")
            @show_if(False)
            @internal_only
            class Example(ApiResource):
                @internal_only
                def get(self):
                    pass
            """,
        )
        output = self.run_hook(filename)
        self.assertIn("Example.get is missing", output)
        self.assertIn("?internal=true", output)

    def test_helpers_and_test_files_are_ignored(self):
        filename = self.write(
            "helpers.py",
            """\
            class Helper:
                def get(self):
                    pass
            """,
        )
        self.write("test/test_example.py", "invalid Python fixture")
        self.write("tests/test_example.py", "invalid Python fixture")
        self.assertIn("0 reminder(s)", self.run_hook(filename))

    def test_syntax_error_warns_without_blocking(self):
        filename = self.write("broken.py", "class")
        self.assertIn("Could not inspect annotations", self.run_hook(filename))

    def test_github_annotations_are_warnings(self):
        filename = self.write(
            "example.py",
            """\
            @resource("/v1/example")
            class Example(ApiResource):
                def delete(self):
                    pass
            """,
        )
        output = self.run_hook(filename, environment={"GITHUB_ACTIONS": "true", "CI": "true"})
        self.assertIn("::warning file=endpoints/api/example.py,line=3", output)
        self.assertNotIn("::error", output)

    def test_robot_token_negative_control(self):
        source = ""
        for account in ("User", "Organization"):
            for suffix, methods in (
                ("Scopes", ["get"]),
                ("Tokens", ["get", "post"]),
                ("Token", ["delete"]),
            ):
                source += f'@resource("/v1/{account}/{suffix}")\n'
                source += f"class {account}{suffix}(ApiResource):\n"
                for method in methods:
                    source += f"    def {method}(self):\n        pass\n"
        filename = self.write("robot_application_tokens.py", source)
        self.assertIn("8 reminder(s)", self.run_hook(filename))
        for account in ("User", "Organization"):
            for suffix, methods in (
                ("Scopes", ["get"]),
                ("Tokens", ["get", "post"]),
                ("Token", ["delete"]),
            ):
                for method in methods:
                    marker = f"class {account}{suffix}(ApiResource):\n"
                    start = source.index(marker) + len(marker)
                    position = source.index(f"    def {method}(self):", start)
                    source = (
                        source[:position]
                        + f'    @nickname("{method}{account}{suffix}")\n'
                        + source[position:]
                    )
        self.write("robot_application_tokens.py", source)
        self.assertIn("0 reminder(s)", self.run_hook(filename))

    def test_missing_python_is_non_blocking(self):
        binaries = self.root / "bin"
        binaries.mkdir()
        git = shutil.which("git")
        if git:
            (binaries / "git").symlink_to(git)
        output = self.run_hook(environment={"PATH": str(binaries)})
        self.assertIn("python3 is unavailable", output)

    def test_checker_failure_is_non_blocking(self):
        binaries = self.root / "bin"
        binaries.mkdir()
        python = binaries / "python3"
        python.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
        python.chmod(0o755)
        output = self.run_hook(environment={"PATH": str(binaries)})
        self.assertIn("could not complete; continuing without blocking", output)


if __name__ == "__main__":
    unittest.main()
