# Contributing to Project Quay

Thank you for your interest in contributing to Project Quay! Whether you're
fixing a typo or building a new feature, this guide will help you get started.

## Your First Contribution

Not sure where to start? Here's the simplest path:

1. Fork the repository on GitHub
2. Clone your fork and create a branch: `git checkout -b docs/fix-typo`
3. Make your change, commit it, and push to your fork
4. Open a PR with a title like `NO-ISSUE: docs: fix typo in README`

You do not need a Jira ticket for small contributions like documentation fixes,
typo corrections, test additions, or minor bug fixes — use the `NO-ISSUE:`
prefix in your PR title. For larger changes (new features, schema changes,
security fixes), file a ticket at
[Red Hat JIRA](https://issues.redhat.com/projects/PROJQUAY) or ask a maintainer
to create one.

We welcome questions at any stage of your contribution. Reach out via the
mailing list or IRC (see [Community](#community) below).

## Getting Started

### Prerequisites

- Docker or Podman (both are fully supported)
- Docker Compose plugin (`docker compose` or `podman compose`)
- Python 3.12
- Node 20+
- pnpm (for frontend development)
- pre-commit (`pip install pre-commit`)

### Local Development

```bash
make local-dev-up                    # Start Quay + PostgreSQL + Redis
make local-dev-up-with-clair         # Include Clair security scanner
make local-dev-down                  # Shutdown
```

| Service    | Address                 |
|------------|-------------------------|
| Quay UI    | http://localhost:8080   |
| PostgreSQL | localhost:5432          |
| Redis      | localhost:6379          |

After starting, navigate to http://localhost:8080 and create an account with
username `admin` to get superuser access. You may need to restart the Quay
container after creating the account: `podman restart quay-quay`.

See [agent_docs/development.md](agent_docs/development.md) for the full setup
guide, including debugging, frontend development, and common troubleshooting.

## Making Changes

### Branch Naming

```
<type>/projquay-<number>-<kebab-case-description>
```

For `NO-ISSUE` contributions, omit the ticket number:

```
<type>/<kebab-case-description>
```

Types: `fix`, `feat`, `test`, `refactor`, `docs`, `chore`

### Coding Conventions

- **Formatting** is handled by pre-commit hooks — run `make install-pre-commit-hook` to set them up.
- **Imports** should follow the ordering patterns already present in each file.
- **Error handling** should use exception types from `endpoints/exception.py` (`NotFound`, `Unauthorized`, `InvalidRequest`, etc.).
- **No secrets** — never commit credentials, API keys, or sensitive configuration.

### Frontend Migration Note

The UI is being migrated from Angular (`static/js/`) to React + PatternFly
(`web/`). All new UI features must be built in React. If you need to modify an
Angular page, check whether a React equivalent already exists in `web/` first.

## Testing

Every code change must include tests.

**Backend (Python):**

```bash
TEST=true PYTHONPATH="." pytest path/to/test.py -v                     # Single file
TEST=true PYTHONPATH="." pytest path/to/test.py::TestClass::test_fn -v # Single test
make unit-test                                                         # All unit tests
make registry-test                                                     # Registry protocol
make types-test                                                        # Type checking (mypy)
```

**Frontend:**

```bash
cd web && pnpm install                          # Install dependencies (first time)
cd web && pnpm run test                         # Vitest unit tests
cd web && pnpm exec playwright test             # All Playwright E2E tests
cd web && pnpm exec playwright test e2e/some.spec.ts  # Single E2E test
```

- **E2E / full-flow tests:** Use Playwright for all new tests (`web/playwright/e2e/`). All E2E tests use Playwright (`web/playwright/e2e/`).
- **Pure unit logic:** Use Vitest only for utilities and data transformers with no UI interaction.

See [agent_docs/testing.md](agent_docs/testing.md) for test fixtures, database
testing, and detailed patterns.

## Commit and PR Format

### PR Title (CI-enforced)

```
PROJQUAY-XXXXX: type(scope): lowercase description
```

Use `NO-ISSUE:` when there is no associated Jira ticket.

Examples:
- `PROJQUAY-1234: fix(api): add pagination to tag listing`
- `NO-ISSUE: docs: fix typo in contributing guide`
- `NO-ISSUE: chore: update dependencies`
- `[redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination`

The title must match this CI-enforced pattern — a `PROJQUAY-` or `QUAYIO-`
ticket reference, or `NO-ISSUE:`, followed by a lowercase conventional commit
type and description:
```
^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
```

### Commit Messages

```
<subsystem>: <what changed> (PROJQUAY-####)

<why this change was made>
```

## Fork Workflow

**Never push directly to `quay/quay`.** Always use a personal fork.

```bash
# Set up your fork (one-time)
gh repo fork quay/quay --clone=false
git remote add fork https://github.com/<your-user>/quay.git

# Push your branch
git push -u fork <branch>

# Open a PR
gh pr create --repo quay/quay --head <your-user>:<branch>
```

## Jira Integration

This section applies to contributors with Red Hat Jira access. If you are an
external contributor using the `NO-ISSUE:` prefix, you can skip this section.

After opening a PR:

1. Comment `/jira refresh` on the PR to link the ticket and validate the target version.
2. Set **Target Version** on the Jira ticket to the current development release before opening the PR — the bot will block merging without it. Check the [PROJQUAY project versions](https://issues.redhat.com/projects/PROJQUAY?selectedItem=com.atlassian.jira.jira-projects-plugin%3Arelease-page) page for the latest unreleased version.

### Ticket Lifecycle

| Status   | Trigger                              |
|----------|--------------------------------------|
| New      | Ticket created                       |
| ASSIGNED | Work begins                          |
| POST     | PR created (set by openshift-ci-robot) |
| MODIFIED | PR merged                            |
| ON_QA    | QE team picks up                     |
| Verified | QA passed                            |
| Closed   | Released                             |

## Code Review

PRs are reviewed by [CodeRabbit](https://coderabbit.ai), an AI code review bot
that runs pre-merge checks:

- PR title and description validation
- Docstring coverage (>= 80% on changed functions)
- Migration safety (no unsafe operations on large tables)
- Migration downgrade existence
- N+1 query prevention
- Read path performance on the v2 registry

**Resolve every inline CodeRabbit comment** — either fix the code or reply
explaining why the comment is not actionable. The bot re-reviews on each push.

## Database Migrations

Always use Alembic to scaffold migration files:

```bash
alembic revision -m "description_of_change"
```

Then edit the generated file in `data/migrations/versions/` to add your
`upgrade()` and `downgrade()` logic.

**Never hand-craft revision IDs** — they cause conflicts when multiple
contributors independently generate migrations.

See [agent_docs/database.md](agent_docs/database.md) for the full database
guide.

## Backporting

If a Jira ticket has a Target Version, backporting is required after merge to
master. Comment `/cherrypick <branch>` on the merged PR and the
`openshift-ci-robot` will create a backport PR.

Release branches follow the `redhat-X.Y` naming pattern. The highest
`redhat-X.Y` branch is synced with master — do not cherry-pick to it. Target
only the older maintained branches.

## Community

- Mailing list: [quay-sig@googlegroups.com](https://groups.google.com/forum/#!forum/quay-sig)
- IRC: #quay on [libera.chat](https://web.libera.chat/?channel=#quay)
- Bug tracking: [Red Hat JIRA](https://issues.redhat.com/projects/PROJQUAY)
- Security issues: [security@redhat.com](mailto:security@redhat.com)
- Community meetings: first Wednesday of every month, 11:00 AM EST

## License

Project Quay is licensed under the [Apache License 2.0](LICENSE). By
contributing, you agree that your contributions will be licensed under the same
terms.

# Certificate of Origin

By contributing to this project you agree to the Developer Certificate of Origin [DCO](../DCO).
This document was created by the Linux Kernel community and is a simple statement that you, as a contributor, have the legal right to make the contribution.
See the [DCO](../DCO) file for details.
