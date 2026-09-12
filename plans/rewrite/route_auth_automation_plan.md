# Route Auth Auto-Verification Plan

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Reduce manual auth checklist review load by auto-verifying routes that follow standard decorator patterns.

## 2. Inputs and outputs

Inputs:
- `plans/rewrite/generated/route_auth_verification_checklist.csv`
- endpoint source files referenced by checklist rows

Outputs:
- updated checklist rows marked `verified-source-anchored` when confidence is high
- `plans/rewrite/generated/route_auth_auto_verification_report.md`

## 3. Automation scope

Auto-verify only when all are true:
1. route method is in a class/function with recognized auth decorators.
2. no conflicting decorators or dynamic auth branch detected.
3. inferred auth mode matches checklist `auth_mode`.

Never auto-verify:
- expression-heavy parser-gap routes
- oauth callback flows with dynamic rule registration
- routes already flagged by manual backlog notes

## 4. Script

- `plans/rewrite/scripts/route_auth_auto_verify.py`

Behavior:
- read checklist CSV
- parse decorators from source using AST
- compare against known auth-mode mapping rules
- update verification status for high-confidence rows
- write report with counts and remaining manual backlog

## 5. Success target

- Reduce manual backlog from 405 rows to fewer than 50 rows before implementation sprint starts.
- Any row not high-confidence stays manual by design.
- Current status: manual backlog is 0 rows (`route_auth_verification_checklist_summary.md`).
