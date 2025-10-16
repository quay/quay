#!/bin/sh -eux
curl -fsSLO https://raw.githubusercontent.com/containerbuildsystem/cachito/master/bin/pip_find_builddeps.py
pip-compile pyproject.toml -o requirements.in --generate-hashes --allow-unsafe
PIP_CONSTRAINT=constraints.txt python3 pip_find_builddeps.py requirements.in --append --only-write-on-update -o requirements-build.in
# we need to do some manipulation to remove conflicting versions
sed -i .back '/setuptools<74/d' requirements-build.in
sed -i .back '/setuptools_scm<8.0/d' requirements-build.in
pip-compile requirements-build.in -o requirements-build.txt --allow-unsafe --generate-hashes
