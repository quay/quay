# Notification Driver Inventory and Migration Plan

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Define parity requirements for notification delivery methods and event emitters.

Primary source anchors:
- `notifications/notificationmethod.py`
- `notifications/notificationevent.py`

## 2. Delivery method inventory

Required method parity list:
1. In-app
2. Email
3. Webhook
4. Flowdock
5. HipChat
6. Slack

## 3. Event inventory policy

- Maintain all currently registered concrete event types (11 in current baseline).
- Concrete event names:
1. `repo_push`
2. `repo_mirror_sync_started`
3. `repo_mirror_sync_success`
4. `repo_mirror_sync_failed`
5. `vulnerability_found`
6. `build_queued`
7. `build_start`
8. `build_success`
9. `build_failure`
10. `build_cancelled`
11. `repo_image_expiry`
- `BaseBuildEvent` is an abstract grouping class (`event_name() -> None`) and is not a deliverable event.
- Preserve payload shape and retry semantics per method.

## 4. Migration strategy

- Implement method adapters behind a single Go notification interface.
- Keep event-to-method routing configuration-compatible.
- Validate outbound payload templates against Python fixtures.

## 5. Test requirements

- Per-method success/failure/retry tests.
- Idempotent delivery tests under duplicate queue delivery.
- Event payload schema compatibility tests.

## 6. Exit criteria

- All methods and events tracked with test IDs.
- Notification queue contract tests pass in mixed and go-only modes.
- Deprecated methods (if any) require explicit decision entry before removal.
