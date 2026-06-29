# Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) for contribution guidelines.

## Contextification Addendum

Start local development with:

```bash
make local-dev-up
make local-dev-up-with-clair
TEST=true PYTHONPATH="." pytest path/to/test.py -v
make unit-test
make registry-test
```

For database changes, update `data/database.py`, generate an Alembic revision, and add downgrade logic where possible. For frontend work, read `web/AGENTS.md` first. Every behavior change should include a focused test note in the PR.
