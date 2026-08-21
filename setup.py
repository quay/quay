import os

from setuptools import find_packages, setup

quay_root = os.path.dirname(os.path.realpath(__file__))
requirementPath = quay_root + "/requirements.txt"
install_requires = []
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        for line in f.read().splitlines():
            # requirements.txt is hash-pinned: a "--hash=..." or "# via ..."
            # continuation line is indented under its package's pin line, so
            # indentation (checked before stripping) is what marks it as a
            # continuation to skip rather than a requirement of its own.
            if line.startswith((" ", "\t")):
                continue
            line = line.strip().rstrip("\\").strip()
            if (
                line
                and not line.startswith("#")
                and not line.startswith("git+")
                and "@" not in line
                and line.split("==")[0] not in ("setuptools", "wheel")
            ):
                install_requires.append(line)

setup(
    name="quay",
    version="3.13",
    description="Quay Modules",
    author="Quay Team",
    author_email="",
    url="https://github.com/quay/quay",
    packages=find_packages(
        exclude=[
            "test",
            "test.*",
            "*.test",
            "*.test.*",
            "*.tests",
            "*.tests.*",
            "web",
            "web.*",
            "conf",
            "conf.*",
            "static",
            "static.*",
            "initdb",
        ],
    ),
    install_requires=install_requires,
)
