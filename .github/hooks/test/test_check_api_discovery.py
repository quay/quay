"""Exercise the advisory Python hook without importing or starting Quay."""

import io
import os
import runpy
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

HOOK = Path(__file__).resolve().parents[1] / "check-api-discovery.py"


class TestAPIDiscoveryReminder(unittest.TestCase):
    def setUp(self):
        """Build a standalone source tree so no Quay services are needed."""
        self.directory = tempfile.TemporaryDirectory(prefix="quay-discovery-hook-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.api = self.root / "endpoints" / "api"
        self.api.mkdir(parents=True)

    def write(self, name, source):
        """Create a source fixture and return its repository-relative path."""
        path = self.api / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return str(path.relative_to(self.root))

    def run_hook(self, *filenames, environment=None):
        """Run the Python entry point and require advisory exit status zero."""
        env = dict(os.environ, GITHUB_ACTIONS="false")
        env.update(environment or {})
        result = subprocess.run(
            [sys.executable, str(HOOK), *filenames],
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

                @operation(["createOne", "createTwo"])
                def post(self):
                    pass

                def options(self):
                    pass

                def head(self):
                    pass
            """,
        )
        self.assertIn("0 reminder(s)", self.run_hook(filename))

    def test_inherited_handlers_require_manual_verification(self):
        """Do not report a clean audit when handlers may come from custom bases."""
        for parent in ["Base", "ImportedBase"]:
            with self.subTest(parent=parent):
                filename = self.write(
                    "example.py",
                    f"""\
                    from another_module import ImportedBase

                    class Base(ApiResource):
                        def get(self):
                            pass

                    @resource("/v1/example")
                    class Example({parent}):
                        pass
                    """,
                )
                output = self.run_hook(filename)
                self.assertIn(f"Example inherits from {parent}", output)
                self.assertIn("inherited HTTP handlers cannot be verified statically", output)

    def test_standard_base_aliases_do_not_need_manual_verification(self):
        """Known Quay bases keep their normal behavior even when imported as aliases."""
        for parent in ["API", "RepoAPI"]:
            with self.subTest(parent=parent):
                filename = self.write(
                    "example.py",
                    f"""\
                    from endpoints.api import ApiResource as API, RepositoryParamResource as RepoAPI

                    @resource("/v1/example")
                    class Example({parent}):
                        @nickname("getExample")
                        def get(self):
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
        self.assertIn(
            "will be omitted from /api/v1/discovery, including with ?internal=true.", output
        )

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
        """Reproduce all eight omitted robot-token operations and their annotations."""
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

    def test_checker_failure_is_non_blocking(self):
        """Unexpected inspection failures remain advisory at the real entry point."""
        output = io.StringIO()
        with patch("pathlib.Path.rglob", side_effect=OSError("inspection failed")):
            with redirect_stdout(output), self.assertRaises(SystemExit) as result:
                runpy.run_path(str(HOOK), run_name="__main__")
        self.assertEqual(result.exception.code, 0)
        self.assertIn("could not complete; continuing without blocking", output.getvalue())


if __name__ == "__main__":
    unittest.main()
