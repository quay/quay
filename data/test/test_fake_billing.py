import fakeredis
import pytest

from data.billing import FakeStripe


@pytest.fixture
def fake_billing(monkeypatch):
    monkeypatch.setattr(FakeStripe, "redis", fakeredis.FakeStrictRedis())
    monkeypatch.setattr(FakeStripe, "ACTIVE_CUSTOMERS", {})
    return FakeStripe


def test_new_customer_is_free_until_checkout_completes(fake_billing):
    customer = fake_billing.Customer.create()
    assert customer.id.startswith("cus_fake_")
    assert customer.subscription is None
    fake_billing.ACTIVE_CUSTOMERS.clear()
    assert fake_billing.Customer.retrieve(customer.id).subscription is None


def test_fake_plan_survives_worker_cache_reset_and_can_be_canceled(fake_billing):
    customer = fake_billing.Customer.create()
    fake_billing.Customer.modify(customer.id, plan="bus-micro-2018")
    fake_billing.ACTIVE_CUSTOMERS.clear()
    restored = fake_billing.Customer.retrieve(customer.id)
    assert restored.subscription.plan.id == "bus-micro-2018"
    fake_billing.Subscription.delete(restored.subscription.id)
    fake_billing.ACTIVE_CUSTOMERS.clear()
    assert fake_billing.Customer.retrieve(customer.id).subscription is None
