**JIRA Process Adherence** (1-5)
Score 1: No JIRA ticket referenced. Ticket not assigned. No target version consideration.
Score 2: Ticket referenced but not assigned to self. Target version ignored.
Score 3: Ticket assigned and referenced in PR title. Target version not checked.
Score 4: Ticket assigned, referenced correctly, target version set when applicable.
Score 5: Full JIRA lifecycle: assigned, referenced in title and commits, target version set, status transitioned, backport triggered if fixVersion requires it.

**Code Quality** (1-5)
Score 1: Code committed without formatting or linting. Tests not run. Type errors present.
Score 2: Basic formatting applied but linting warnings ignored. Minimal test coverage.
Score 3: Black + isort formatting applied. Flake8 passes. Unit tests written for new code.
Score 4: All formatting/linting clean. Good test coverage including edge cases. MyPy passes.
Score 5: Pristine code quality. Pre-commit hooks all pass. Comprehensive tests (unit + integration). No N+1 queries. Migration safety verified for large tables. Performance considered for read path.

**PR Conventions** (1-5)
Score 1: PR title doesn't match required format. No description. No labels.
Score 2: PR title has JIRA reference but wrong format. Minimal description.
Score 3: PR title matches `PROJQUAY-XXXX: type(scope): description` format. Basic description with summary.
Score 4: Correct title format. Description follows template (Summary, Root Cause/Rationale, Test Plan). Area labels applied.
Score 5: Perfect PR: correct title, full description template, appropriate labels, linked JIRA ticket, test plan with checkboxes, no WIP markers.

**CI & Review Responsiveness** (1-5)
Score 1: CI failures ignored. CodeRabbit feedback not addressed. No follow-up.
Score 2: Aware of CI failures but no action taken. CodeRabbit feedback partially read.
Score 3: CI failures investigated and fixed. CodeRabbit suggestions acknowledged.
Score 4: All CI checks passing. CodeRabbit actionable feedback addressed. Codecov coverage maintained or improved.
Score 5: All CI green. CodeRabbit pre-merge checks all passing. All review comments addressed. Coverage improved. Migration chain validated. Alembic head verified.
