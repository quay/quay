#!/bin/sh -eux
# Regenerates requirements.txt with sha256 hashes via pip-compile, so pip's
# hash-checking mode (`--require-hashes`, used by Dockerfile/Dockerfile.downstream)
# can verify every package Hermeto/Konflux prefetches, not just its pinned version.
#
# requirements.txt pins a few forked dependencies via `git+https://` URLs.
# pip's hash-checking mode rejects VCS requirements outright, so they're
# rewritten here as direct HTTPS archive URLs (GitHub serves any commit as a
# stable tarball at this path), which pip-compile can hash like any other
# package. The URL must end in a recognized archive extension (.tar.gz, .zip,
# etc.) -- Hermeto's prefetch statically validates the URL's suffix and
# rejects a codeload.github.com/.../tar.gz/<sha> URL, since "tar.gz" there is
# a path segment, not a filename suffix.
#
# Must be run with Python 3.12 (matching Dockerfile/Dockerfile.downstream) on
# Linux with the same build toolchain as Dockerfile.downstream's build-python
# stage (gcc-c++, libpq-devel, libffi-devel, openssl-devel, etc.) — some
# runtime deps (e.g. psycopg2) have no macOS wheels for the pinned version and
# fail to resolve without those headers.
sed -E 's|^([A-Za-z0-9_.-]+) @ git\+https://github\.com/([^/]+)/([^.]+)\.git@([0-9a-f]{40})$|\1 @ https://github.com/\2/\3/archive/\4.tar.gz|' requirements.txt > requirements.in
pip-compile --generate-hashes --allow-unsafe -o requirements.txt requirements.in
rm -f requirements.in
