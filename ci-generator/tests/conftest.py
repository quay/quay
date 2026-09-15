"""Shared paths for ci-generator tests."""

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
PHASE0_MATRIX = FIXTURES_DIR / "matrix-phase0.yaml"
