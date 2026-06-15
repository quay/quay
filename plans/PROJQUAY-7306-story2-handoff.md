# PROJQUAY-7306 Story 2 Handoff — Namespace notification model CRUD + API endpoints

## Status: COMPLETE

**Commit:** `PROJQUAY-7306: feat(quota): add namespace notification CRUD model and API endpoints (Story 2)`
**Branch:** `feat/projquay-7306-quota-warning-notifications`
**Tests:** All 21 tests passing in `endpoints/api/test/test_namespacenotification.py` + 47 Story 1 tests + 6 quota tests (no regressions)

---

## What Was Done

### Files Modified

| File | Change |
|------|--------|
| `data/model/notification.py` | Added 7 namespace notification model functions: `create_namespace_notification()`, `list_namespace_notifications()`, `get_namespace_notification()`, `delete_namespace_notification()`, `reset_namespace_notification_number_of_failures()`, `increment_namespace_notification_failure_count()`, `get_enabled_namespace_notification()` |
| `endpoints/api/__init__.py` | Registered `endpoints.api.namespacenotification` module import |
| `initdb.py` | Added `LogEntryKind` rows for `create_namespace_notification`, `delete_namespace_notification`, `reset_namespace_notification` |
| `test/testconfig.py` | Added `FEATURE_QUOTA_NOTIFICATIONS = True` to `TestConfig` for test-time `show_if` evaluation |

### Files Created

| File | Purpose |
|------|---------|
| `endpoints/api/namespacenotification.py` | REST API endpoints for org and user namespace notification CRUD |
| `endpoints/api/test/test_namespacenotification.py` | 21 tests covering CRUD, permissions, event validation, audit logging |
| `data/migrations/versions/9fa37f66a9b6_add_namespace_notification_log_entry_.py` | Alembic migration: seeds `LogEntryKind` rows for namespace notification audit actions |

### API Endpoints Implemented

**Organization endpoints** (gated by `FEATURE_QUOTA_NOTIFICATIONS`, requires org admin + superuser bypass):
- `GET /v1/organization/<orgname>/notifications` — list namespace notifications
- `POST /v1/organization/<orgname>/notifications` — create namespace notification
- `GET /v1/organization/<orgname>/notifications/<uuid>` — get single notification
- `DELETE /v1/organization/<orgname>/notifications/<uuid>` — delete notification
- `POST /v1/organization/<orgname>/notifications/<uuid>` — reset failure count
- `POST /v1/organization/<orgname>/notifications/<uuid>/test` — queue test notification

**User endpoints** (gated by `FEATURE_QUOTA_NOTIFICATIONS`, requires `@require_user_admin()`):
- `GET /v1/user/notifications` — list namespace notifications
- `POST /v1/user/notifications` — create namespace notification
- `GET /v1/user/notifications/<uuid>` — get single notification
- `DELETE /v1/user/notifications/<uuid>` — delete notification
- `POST /v1/user/notifications/<uuid>` — reset failure count
- `POST /v1/user/notifications/<uuid>/test` — queue test notification

### Key Design Decisions

1. **Event validation:** Create endpoint validates event name is `quota_warning` or `quota_error` only — namespace notifications are quota-specific.
2. **Method validation:** Skips repo-level email authorization check (used by `EmailMethod.validate`) since namespace notifications don't belong to a repository. Only validates the method name exists.
3. **Feature gating:** Uses `@show_if(features.QUOTA_NOTIFICATIONS)` — requires `FEATURE_QUOTA_NOTIFICATIONS = True` in both app config and test config (for import-time evaluation).
4. **Permission model:** Org endpoints use `AdministerOrganizationPermission` with `SuperUserPermission` bypass. User endpoints use `@require_user_admin()`.
5. **Response format:** Mirrors repo notification pattern: `{uuid, title, event, method, config, event_config, number_of_failures}`.

---

## Next Story: Story 3 — Dedup / cooldown logic

### What to Build

Add deduplication and cooldown logic to prevent notification spam. When a quota threshold is crossed, the system should check `QuotaNotificationState` to see if a notification was already sent recently (within `QUOTA_NOTIFICATION_COOLDOWN_SECONDS`) and skip if so.

### Dependencies Available

Story 3 depends on Story 1 (complete). The following are available:
- `QuotaNotificationState` model in `data/database.py` (threshold_percent, last_notified_at, cleared)
- `QUOTA_NOTIFICATION_COOLDOWN_SECONDS` config value (default: 86400)
- `NamespaceNotification` model and CRUD functions from Story 2

### Key Reference Files

- `data/database.py:1660` — `QuotaNotificationState` model
- `config.py:891-892` — `QUOTA_NOTIFICATION_COOLDOWN_SECONDS` default
- `data/model/notification.py` — namespace notification model functions (pattern to follow for state management)

---

## Dependency Graph (Remaining Stories)

```
1 (Foundation) ✅ DONE
├── 2 (Model + API) ✅ DONE
│   ├── 4 (Dispatch) — needs 2, 3
│   │   ├── 5 (Email routing)
│   │   ├── 6 (Push-triggered)
│   │   ├── 7 (Retroactive) — also needs 2
│   │   └── 8 (Periodic worker)
│   └── 9 (Frontend)
├── 3 (Dedup) ◀── NEXT — needs 1 only
└── 10 (Cleanup) — needs 1, 3
```

**Recommended execution order:** 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

---

## Instructions for Next Agent Session

### General Workflow

1. You are implementing the stories for epic PROJQUAY-7306 / PROJQUAY-11800 one at a time, in dependency order.
2. All work is on branch `feat/projquay-7306-quota-warning-notifications`.
3. Each story must be a **separate commit** so each story's work is independently identifiable.
4. After completing your story, create a handoff document at `plans/PROJQUAY-7306-story{N}-handoff.md` following this same format.
5. The handoff document must include all these instructions so the next agent session can continue the chain.

### Key Documents

- **Epic plan:** `/Users/sridiptamisra/git/quay/.claude/plans/PROJQUAY-7306-epic.md`
- **Design decisions:** `/Users/sridiptamisra/sri/projquay-7306-design-decisions.md`
- **Stories breakdown:** `/Users/sridiptamisra/sri/projquay-7306-stories.md`
- **Dev-team workflow:** `/Users/sridiptamisra/git/quay/plans/dev-team-prompt.md`
- **This handoff:** `/Users/sridiptamisra/git/quay/plans/PROJQUAY-7306-story2-handoff.md`

### Dev-Team Workflow

Use the dev-team workflow defined in `plans/dev-team-prompt.md`:
1. **Phase 1 — Classify and Scope:** Investigate the codebase patterns relevant to your story
2. **Phase 2 — Design the Team:** Select agents (Implementer, QE, Checker minimum for code tasks)
3. **Phase 3 — Present Plan:** Show the plan and ask "Ready to proceed, or adjust?"
4. **Phase 4 — Execute:** Create tasks, implement changes, run tests
5. **Phase 5 — Deliver:** Summarize changes, commit, create handoff

### Testing Requirements

- **All unit tests must be run using the project virtual environment** at `.venv/bin/python` before committing:
  ```bash
  TEST=true PYTHONPATH="." .venv/bin/python -m pytest path/to/test_file.py -v
  ```
- System Python (`python3`) does not have Flask/Peewee installed — tests will fail with `ModuleNotFoundError`.
- All tests must be passing before committing and handing off.

### Commit Message Format

```
PROJQUAY-7306: type(scope): lowercase description (Story N)
```

### Alembic Migration Convention

**Never hand-craft migration files or fabricate revision IDs.** Always use `alembic revision -m "description"` to scaffold. The current migration HEAD is `9fa37f66a9b6` (from Story 2).
