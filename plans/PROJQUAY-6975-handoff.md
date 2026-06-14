# PROJQUAY-6975: Implementation Handoff Document

**Epic:** PROJQUAY-6975 — Allow Single Email for Multiple Organizations
**Branch:** `feat/projquay-6975-single-email-multiple-orgs`
**Last updated:** 2026-06-14
**Status:** All 7 stories complete — ready for PR

---

## What Has Been Done

### Branch Setup

- Created branch `feat/projquay-6975-single-email-multiple-orgs` from latest `origin/master` (commit `5ef6b0513`)
- Cherry-picked and reorganized work from PR #6045 (`feat/projquay-10589-contact-email-crud`) into a clean Story 1 commit
- PR #6045 should be abandoned — all epic work continues on this branch

### Story 1: PROJQUAY-10589 — Backend CRUD + UUID Org Email (COMPLETE)

**Commit:** `PROJQUAY-10589: feat(model): add contact_email CRUD and UUID org email`

**Files changed:**
- `data/model/organization.py` — Modified `create_organization()` + added 4 CRUD functions
- `data/model/test/test_organization.py` — Added 3 test classes (14 new tests)

**What was implemented:**
1. `create_organization()` now generates a UUID for `User.email` and accepts optional `contact_email` parameter
2. `effective_contact = contact_email or email` — backward compat: if caller passes `email` but no `contact_email`, the email is stored as contact_email
3. `email_required` parameter kept in signature for backward compat with callers like `endpoints/v2/v2auth.py:352`
4. Four new CRUD functions: `get_contact_email()`, `set_contact_email()`, `delete_contact_email()`, `find_organizations_by_contact_email()`

**Tests:** All 30 tests pass (`TEST=true PYTHONPATH="." .venv/bin/python -m pytest data/model/test/test_organization.py -v`)

**Note:** You may need to install `regex` in the venv first: `.venv/bin/pip install regex`

### Story 2: PROJQUAY-10591 — API Endpoints (COMPLETE)

**Commit:** `PROJQUAY-10591: feat(api): expose contact_email in organization endpoints`

**Files changed:**
- `endpoints/api/organization.py` — Modified `org_view()`, `NewOrg` schema, `OrganizationList.post()`, `UpdateOrg` schema, `Organization.put()`, `ApplicationInformation.get()`
- `endpoints/api/test/test_organization.py` — Added `TestContactEmail` class (8 new tests)

**What was implemented:**
1. `org_view()` now returns `contact_email` from the model (admin-only); `email` field set to contact_email value for backward compat; internal UUID email never exposed
2. `NewOrg` and `UpdateOrg` schemas updated with `contact_email` property
3. `OrganizationList.post()` — removed `FEATURE_MAILING` email requirement; extracts `contact_email` (falling back to `email` field for backward compat); validates email format; passes `contact_email` to `create_organization()`
4. `Organization.put()` — replaced old email update block (which had a uniqueness check on `User.email`) with `contact_email` upsert via `model.organization.set_contact_email()` — no uniqueness constraint, allows duplicate emails across orgs
5. `ApplicationInformation.get()` — avatar email fallback now tries `contact_email` before the internal UUID email
6. Audit log entries updated to use `contact_email` key

**Tests:** All 21 tests pass (`TEST=true PYTHONPATH="." .venv/bin/python -m pytest endpoints/api/test/test_organization.py -v`), all 30 model tests still pass

**Gotchas for next agent:**
- The `or` operator precedence in `org_view()` line 124 (`contact_email or "" if (is_admin or can_view_as_superuser) else ""`) is intentional — Python evaluates it as `(contact_email or "") if condition else ""`, which is correct because when condition is True, it yields contact_email or empty string
- `Organization.put()` now uses `or` to check both `contact_email` and `email` fields from the request body (`org_data.get("contact_email") or org_data.get("email")`), so old clients sending `email` still work

### Story 3: PROJQUAY-10590 — Email Notification Routing (COMPLETE)

**Commit:** `PROJQUAY-10590: feat(email): route notifications via contact_email`

**Files changed:**
- `util/useremails.py` — Modified `send_org_recovery_email()` to accept optional `contact_email` parameter; sends to contact_email if set, otherwise fans out to each admin
- `endpoints/api/user.py` — Rewrote `Recovery.post()` with dual-lookup logic (user + org by contact_email)
- `endpoints/webhooks.py` — Updated invoice, subscription, and payment-failed email routing to use `contact_email` with admin fallback for orgs
- `web/src/routes/Signin/Signin.tsx` — Updated recovery success message to be generic
- `util/test/test_useremails.py` — Added 3 tests for `send_org_recovery_email()`
- `endpoints/api/test/test_user.py` — Added `TestRecoveryPost` class (5 tests)

**What was implemented:**
1. `Recovery.post()` now always does BOTH lookups: `find_user_by_email()` for personal users AND `find_organizations_by_contact_email()` for orgs — the same email can match both
2. Always returns `{"status": "sent"}` regardless of matches — never leaks account existence
3. Orgs found via `find_user_by_email()` are ignored (the `user.organization` check skips them); orgs are only handled via the contact_email lookup
4. Billing webhooks (invoice, subscription, payment-failed) now route through `contact_email` with admin fallback for org namespaces
5. Frontend recovery message updated to: "Recovery instructions have been sent to {email} for any accounts associated to the email."

**Deviations from original implementation plan:**
- **Always-both-lookups:** Original plan said do `find_user_by_email()` first, then only `find_organizations_by_contact_email()` if no user found. Revised to always do both, because the same email can be a personal user's email AND an org's contact_email.
- **Always-return-sent:** Original plan returned `"org"` status for org matches. Revised to always return `"sent"` for security (no account existence leakage).
- **Frontend message:** Updated to match the always-sent behavior. The `status === "org"` branch in Signin.tsx is now dead code (left for cleanup).
- **Separate emails:** For now, personal user and org recovery send separate emails using existing templates. A unified single-email approach is deferred to Story 6 (PROJQUAY-11799).

**Tests:** All 14 useremails tests pass, all 5 recovery endpoint tests pass

### Story 4: PROJQUAY-10592 — React Create Organization Modal (COMPLETE)

**Commit:** `PROJQUAY-10592: feat(ui): update create org modal with optional contact email`

**Files changed:**
- `web/src/resources/OrganizationResource.ts` — Added `contact_email` to `IOrganization` interface; updated `CreateOrgRequest` and `createOrg()` to use `contact_email` instead of `email`; added `contact_email` to `updateOrgSettingsParams`
- `web/src/hooks/UseOrganizations.ts` — Renamed `email` parameter to `contactEmail` in `createOrganizationMutator` and exposed `createOrganization` function
- `web/src/routes/OrganizationsList/CreateOrganizationModal.tsx` — Replaced mandatory "Organization Email" with optional "Contact Email (Optional)"; removed `mailingEnabled` gating and `useQuayConfig` dependency; renamed state `organizationEmail` → `contactEmail`; updated helper text; removed email from button disabled check

**What was implemented:**
1. Email field always visible (no longer gated by `FEATURE_MAILING`)
2. Email field is optional — org can be created with just a name
3. Label changed: "Organization Email" → "Contact Email (Optional)"
4. Helper text: "Optional. Used for organization recovery and notifications."
5. Form submits `contact_email` to the API (not `email`)
6. `onInputBlur` clears validation error when field is emptied
7. `IOrganization` interface extended with `contact_email?: string`
8. `updateOrgSettingsParams` extended with `contact_email?: string` (prep for Story 5)

**Type checks:** No TypeScript errors in modified files

### Story 5: PROJQUAY-10593 — React Organization Settings (COMPLETE)

**Commit:** `PROJQUAY-10593: feat(ui): update org settings to manage contact email`

**Files changed:**
- `web/src/routes/OrganizationsList/Organization/Tabs/Settings/GeneralSettings.tsx` — Email field now initializes from `contact_email`, label changed to "Contact Email" for orgs, helper text updated, validation allows empty, submit sends `contact_email`
- `endpoints/api/organization.py` — Fixed `Organization.put()` to handle empty string for clearing contact_email (was treating `""` as falsy via Python `or` operator); uses `delete_contact_email()` when clearing
- `endpoints/api/test/test_organization.py` — Added `test_clear_contact_email` test
- `web/playwright/e2e/organization/settings.spec.ts` — Replaced "Duplicate Email on Update" test (obsolete — uniqueness constraint removed) with 4 new "Contact Email" tests: label/helper text verification, duplicate emails allowed, PUT payload verification, clearing email

**What was implemented:**
1. Email field initializes from `organization?.contact_email` instead of `organization?.email` (internal UUID hidden)
2. Label changed: "Email" → "Contact Email" for organizations; user accounts unchanged
3. Helper text for orgs: "Optional. Used for organization recovery and billing notifications."
4. Validation: allows empty email (optional field), validates format only when non-empty
5. Submit handler sends `contact_email` to the API instead of `email`
6. Backend bugfix: `Organization.put()` now properly handles clearing contact_email by using `delete_contact_email()` when an empty string is sent, and uses explicit key presence check (`"contact_email" in org_data`) instead of Python `or` operator to avoid treating `""` as falsy

**Tests:** All 22 API tests pass, all 30 model tests pass, 4 new Playwright E2E tests added

### Story 6: PROJQUAY-11799 — Unified Recovery Email Template (COMPLETE)

**Commit:** `PROJQUAY-11799: feat(email): unified recovery email for combined user + org scenarios`

**Files changed:**
- `emails/combinedrecovery.html` — New Jinja2 template with conditional org section (iterates over orgs with admin usernames) and conditional user section (password reset link when `reset_token` is present)
- `util/useremails.py` — Added `send_combined_recovery_email(email, orgs_with_admins, reset_token=None)` function that sends a single combined email using the new template
- `endpoints/api/user.py` — Updated `Recovery.post()` to build `orgs_with_admins` list and call `send_combined_recovery_email()` when orgs are found, with optional `reset_token` when a personal user also matches; falls back to `send_recovery_email()` when only a personal user matches
- `util/test/test_useremails.py` — Added 2 parametrized template render tests for `combinedrecovery`, plus 4 dedicated tests: `test_send_combined_recovery_with_user_and_orgs`, `test_send_combined_recovery_orgs_only`, `test_render_combined_recovery_template`, `test_render_combined_recovery_template_no_reset`
- `endpoints/api/test/test_user.py` — Updated all 5 existing `TestRecoveryPost` tests to use `send_combined_recovery_email` patches instead of `send_org_recovery_email`; added `test_recovery_multiple_orgs` test

**What was implemented:**
1. New `combinedrecovery.html` template that combines org recovery info (listing all matching orgs with their admin usernames) and optional password reset link into a single email
2. `send_combined_recovery_email()` accepts a list of `{org_name, admin_usernames}` dicts and an optional `reset_token`; includes GmailAction metadata when a reset token is present
3. `Recovery.post()` now consolidates all recovery information into a single email when orgs are found:
   - **Orgs only:** Sends combined email with org section, no reset link
   - **User + orgs:** Sends combined email with both org section and password reset link
   - **User only:** Uses existing `recovery.html` template (unchanged)
   - **No match:** Returns `{"status": "sent"}` silently (unchanged)
4. The `send_org_recovery_email()` function is preserved for use by other callers (webhooks) but is no longer called from the recovery endpoint

**Tests:** All 20 useremails tests pass, all 12 user endpoint tests pass

### Story 7: PROJQUAY-6975 — Playwright E2E Tests (COMPLETE)

**Commit:** `PROJQUAY-6975: test(e2e): add Playwright tests for contact email feature`

**Files changed:**
- `web/playwright/utils/api/client.ts` — Updated `createOrganization()` to send `contact_email` instead of `email`; added `getOrganization()` method
- `web/playwright/fixtures.ts` — Updated `TestApi.organization()` to accept optional `contactEmail` parameter; added `contactEmail` to `CreatedOrg` interface
- `web/playwright/e2e/organization/contact-email.spec.ts` — New test file with 5 test groups (15 tests): Create Org Modal, Org Settings, E2E Lifecycle, API Contract, Recovery Flow
- `web/playwright/e2e/organization/org-list.spec.ts` — Removed `mailingEnabled` conditionals from CRUD lifecycle test; rewrote FEATURE_MAILING test to verify email is always visible and optional

**What was implemented:**
1. API client updated: `createOrganization()` sends `contact_email` (not `email`); body only includes `contact_email` when provided
2. Fixtures updated: `TestApi.organization()` passes `contactEmail` through; `CreatedOrg` interface includes `contactEmail` field
3. New `contact-email.spec.ts` with consolidated tests covering:
   - **Group 1:** Create modal — field visibility, label, helper text, validation cycle, shared email
   - **Group 2:** Settings — display, label, validation, update persistence, clear, shared email, user label regression
   - **Group 3:** E2E lifecycle — create → settings → update → reload; create without email → add in settings; UUID never exposed
   - **Group 4:** API contract — GET returns `contact_email`, backward compat with `email` field in POST, FEATURE_MAILING decoupled
   - **Group 5:** Recovery — generic "sent" message for any email type (no info leak)
4. Existing `org-list.spec.ts` updated: removed all `mailingEnabled`/`quayConfig` conditionals from CRUD lifecycle; rewrote FEATURE_MAILING test

---

## All Stories Complete

| Order | Story | JIRA | Status |
|-------|-------|------|--------|
| 1 | Backend CRUD + UUID org email | PROJQUAY-10589 | DONE |
| 2 | API endpoints | PROJQUAY-10591 | DONE |
| 3 | Email notification routing | PROJQUAY-10590 | DONE |
| 4 | React Create Org modal | PROJQUAY-10592 | DONE |
| 5 | React Org Settings | PROJQUAY-10593 | DONE |
| 6 | Unified recovery email template | PROJQUAY-11799 | DONE |
| 7 | Playwright E2E tests | PROJQUAY-6975 | DONE |

All implementation and testing is complete. Ready for PR creation and code review.

---

## Instructions for the Next Agent Session

### Context

You are implementing epic PROJQUAY-6975 (Allow Single Email for Multiple Organizations) for the Quay container registry. The work is organized as sequential stories, each committed separately on the same branch.

### Plan Documents (READ THESE FIRST)

1. **Implementation Plan:** `/Users/sridiptamisra/git/quay/plans/PROJQUAY-6975-implementation-plan.md`
   - Contains full implementation details for all 5 stories
   - Follow this plan STRICTLY for the story you are implementing
   - Line numbers were validated on 2026-05-25 — verify before editing

2. **Playwright Test Plan:** `/Users/sridiptamisra/git/quay/plans/PROJQUAY-6975-playwright-test-plan.md`
   - E2E test specifications for Stories 4 and 5 + cross-cutting scenarios
   - Implement as the final commit after all stories are done

3. **Dev Team Workflow:** `/Users/sridiptamisra/git/quay/plans/dev-team-prompt.md`
   - Use this workflow for implementation: classify, design team, present plan, execute, deliver

### Workflow for Your Story

1. **Read** this handoff document, the implementation plan (your story's section), and the dev-team workflow
2. **Read** the relevant agent docs before coding:
   - API work: `agent_docs/api.md`
   - Database/model work: `agent_docs/database.md`
   - Testing: `agent_docs/testing.md`
   - React frontend: `web/AGENTS.md`
3. **Verify** you are on branch `feat/projquay-6975-single-email-multiple-orgs`
4. **Pull latest** if the branch has been pushed: `git pull`
5. **Implement** your story following the implementation plan strictly
6. **Run tests** as specified in the plan for your story
7. **Commit** with message format: `PROJQUAY-XXXXX: type(scope): description`
   - Include `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`
8. **Update this handoff document:**
   - Mark your story as DONE in the status table
   - Update "What Has Been Done" with your story's details
   - Set the next story as **NEXT**
   - Update the "Last updated" date
9. **Commit the updated handoff** as part of your story's commit (or as a separate small commit)

### Branch & Commit Convention

- **Branch:** `feat/projquay-6975-single-email-multiple-orgs` (already created, use it)
- **Commit per story:** Each story = one commit with message `PROJQUAY-XXXXX: type(scope): description`
- **Do NOT create separate branches per story** — all work goes on this single branch
- **Do NOT push to `quay/quay` directly** — use the fork remote

### Key Conventions (from AGENTS.md)

- Follow existing import ordering patterns in each file
- Use pre-commit hooks for formatting (run automatically on commit)
- Never commit secrets or credentials
- Use appropriate exception types from `endpoints/exception.py`
- Every code change must include tests

### Testing

- Backend: `TEST=true PYTHONPATH="." .venv/bin/python -m pytest <test-file> -v`
- Frontend: See `web/AGENTS.md`
- You may need to install `regex` in venv: `.venv/bin/pip install regex`

### Reference: PR #6045

The original PR #6045 (`feat/projquay-10589-contact-email-crud`) contained partial implementations for Stories 2, 3, and 5 in addition to Story 1. These were NOT brought into the new branch — implement each story fresh from the plan. The PR can be referenced for context but the implementation plan is the source of truth.

Key differences from the PR that were intentionally corrected:
- `email_required` parameter was kept in `create_organization()` signature (PR removed it, but `v2auth.py` still passes it)
- Only Story 1 model-layer changes were committed; API/email/frontend changes left for their respective stories

---

## Architecture Quick Reference

```
User table
├── id
├── username
├── email (UNIQUE) ← auto-generated UUID for orgs (Story 1)
└── organization (bool)

OrganizationContactEmail table (already existed from PROJQUAY-10588)
├── id
├── organization_id (FK → User.id, UNIQUE) ← one-to-one
└── contact_email (nullable, indexed, NOT unique) ← user-facing email

Key functions (data/model/organization.py):
├── create_organization(name, email, creating_user, email_required=True, is_possible_abuser=False, contact_email=None)
├── get_contact_email(org) → str | None
├── set_contact_email(org, contact_email) → OrganizationContactEmail
├── delete_contact_email(org) → None
└── find_organizations_by_contact_email(contact_email) → Query[User]
```
