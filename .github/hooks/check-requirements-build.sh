#!/bin/bash
# Pre-commit hook: ensure requirements-build.txt is updated when requirements.txt changes

if git diff --cached --name-only | grep -q "^requirements\.txt$"; then
    if ! git diff --cached --name-only | grep -q "^requirements-build\.txt$"; then
        echo "requirements.txt was modified but requirements-build.txt was not updated."
        echo "Run: pybuild-deps compile --generate-hashes --output-file=requirements-build.txt requirements.txt"
        exit 1
    fi
fi
