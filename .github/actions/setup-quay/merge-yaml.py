#!/usr/bin/env python3
"""Merge YAML files (later files override earlier ones)."""
import sys

import yaml


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (override wins)."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <base.yaml> <override.yaml> [more.yaml...]", file=sys.stderr)
        sys.exit(1)

    result = {}
    for path in sys.argv[1:]:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        result = deep_merge(result, data)

    yaml.dump(result, sys.stdout, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    main()
