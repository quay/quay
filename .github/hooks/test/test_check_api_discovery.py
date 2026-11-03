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
        """Run the real shell entry point and require advisory exit status zero."""
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

    def test_multi_route_nickname_cardinality_warns_without_blocking(self):
        """Both scalar IDs and undersized ID lists can break runtime discovery."""
        for routes in ['"/v1/one", "/v1/two"', '*["/v1/one", "/v1/two"]']:
            for nickname in ['"getExample"', '["getExample"]']:
                with self.subTest(routes=routes, nickname=nickname):
                    filename = self.write(
                        "example.py",
                        f"""\
                        @resource({routes})
                        class Example(ApiResource):
                            @nickname({nickname})
                            def get(self):
                                pass
                        """,
                    )
                    output = self.run_hook(filename)
                    if routes.startswith("*"):
                        self.assertIn("could not determine the route count", output)
                    else:
                        self.assertIn("serves 2 routes", output)
                        self.assertIn("only 1 operation ID(s)", output)

    def test_stacked_resource_decorators_need_distinct_ids(self):
        filename = self.write(
            "example.py",
            """\
            @resource("/v1/one")
            @resource("/v1/two")
            class Example(ApiResource):
                @nickname("getExample")
                def get(self):
                    pass
            """,
        )
        self.assertIn("serves 2 routes", self.run_hook(filename))

    def test_method_specific_routes_do_not_require_extra_ids(self):
        filename = self.write(
            "example.py",
            """\
            @resource("/v1/one", methods=["get"])
            @resource("/v1/two", methods=["POST"])
            class Example(ApiResource):
                @nickname("getExample")
                def get(self):
                    pass

                @nickname("createExample")
                def post(self):
                    pass
            """,
        )
        self.assertIn("0 reminder(s)", self.run_hook(filename))

    def test_dynamic_methods_require_manual_route_count_verification(self):
        filename = self.write(
            "example.py",
            """\
            @resource("/v1/example", methods=ALLOWED_METHODS)
            class Example(ApiResource):
                @nickname("getExample")
                def get(self):
                    pass
            """,
        )
        self.assertIn("could not determine the route count", self.run_hook(filename))

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
