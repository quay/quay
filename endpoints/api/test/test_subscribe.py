from unittest.mock import MagicMock

from endpoints.api.subscribe import subscription_view


def _make_subscription(plan_id="bus-medium-2018", status="active", used_repos=3):
    sub = MagicMock()
    sub.plan.id = plan_id
    sub.status = status
    sub.current_period_start = 1700000000
    sub.current_period_end = 1702592000
    sub.trial_start = None
    sub.trial_end = None
    return sub


def test_subscription_view_includes_status():
    sub = _make_subscription(status="active")
    view = subscription_view(sub, 3)
    assert "status" in view, "subscription_view must return a 'status' field"
    assert view["status"] == "active"


def test_subscription_view_past_due_status():
    sub = _make_subscription(status="past_due")
    view = subscription_view(sub, 5)
    assert view["status"] == "past_due"


def test_subscription_view_trialing_status():
    sub = _make_subscription(status="trialing")
    view = subscription_view(sub, 0)
    assert view["status"] == "trialing"
