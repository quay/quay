import stripe

from datetime import datetime, timedelta
from calendar import timegm

from util.morecollections import AttrDict

PLANS = [
    # Deprecated Plans (2013-2014)
    {
        "title": "Micro",
        "price": 700,
        "privateRepos": 5,
        "stripeId": "micro",
        "audience": "For smaller teams",
        "bus_features": False,
        "deprecated": True,
        "free_trial_days": 14,
        "superseded_by": "personal-30",
        "plans_page_hidden": False,
    },
    {
        "title": "Basic",
        "price": 1200,
        "privateRepos": 10,
        "stripeId": "small",
        "audience": "For your basic team",
        "bus_features": False,
        "deprecated": True,
        "free_trial_days": 14,
        "superseded_by": "bus-micro-30",
        "plans_page_hidden": False,
    },
    {
        "title": "Yacht",
        "price": 5000,
        "privateRepos": 20,
        "stripeId": "bus-coreos-trial",
        "audience": "For small businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 180,
        "superseded_by": "bus-small-30",
        "plans_page_hidden": False,
    },
    {
        "title": "Personal",
        "price": 1200,
        "privateRepos": 5,
        "stripeId": "personal",
        "audience": "Individuals",
        "bus_features": False,
        "deprecated": True,
        "free_trial_days": 14,
        "superseded_by": "personal-30",
        "plans_page_hidden": False,
    },
    {
        "title": "Skiff",
        "price": 2500,
        "privateRepos": 10,
        "stripeId": "bus-micro",
        "audience": "For startups",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 14,
        "superseded_by": "bus-micro-30",
        "plans_page_hidden": False,
    },
    {
        "title": "Yacht",
        "price": 5000,
        "privateRepos": 20,
        "stripeId": "bus-small",
        "audience": "For small businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 14,
        "superseded_by": "bus-small-30",
        "plans_page_hidden": False,
    },
    {
        "title": "Freighter",
        "price": 10000,
        "privateRepos": 50,
        "stripeId": "bus-medium",
        "audience": "For normal businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 14,
        "superseded_by": "bus-medium-30",
        "plans_page_hidden": False,
    },
    {
        "title": "Tanker",
        "price": 20000,
        "privateRepos": 125,
        "stripeId": "bus-large",
        "audience": "For large businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 14,
        "superseded_by": "bus-large-30",
        "plans_page_hidden": False,
    },
    # Deprecated plans (2014-2017)
    {
        "title": "Personal",
        "price": 1200,
        "privateRepos": 5,
        "stripeId": "personal-30",
        "audience": "Individuals",
        "bus_features": False,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "personal-2018",
        "plans_page_hidden": False,
    },
    {
        "title": "Skiff",
        "price": 2500,
        "privateRepos": 10,
        "stripeId": "bus-micro-30",
        "audience": "For startups",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "bus-micro-2018",
        "plans_page_hidden": False,
    },
    {
        "title": "Yacht",
        "price": 5000,
        "privateRepos": 20,
        "stripeId": "bus-small-30",
        "audience": "For small businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "bus-small-2018",
        "plans_page_hidden": False,
    },
    {
        "title": "Freighter",
        "price": 10000,
        "privateRepos": 50,
        "stripeId": "bus-medium-30",
        "audience": "For normal businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "bus-medium-2018",
        "plans_page_hidden": False,
    },
    {
        "title": "Tanker",
        "price": 20000,
        "privateRepos": 125,
        "stripeId": "bus-large-30",
        "audience": "For large businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "bus-large-2018",
        "plans_page_hidden": False,
    },
    {
        "title": "Carrier",
        "price": 35000,
        "privateRepos": 250,
        "stripeId": "bus-xlarge-30",
        "audience": "For extra large businesses",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "bus-xlarge-2018",
        "plans_page_hidden": False,
    },
    {
        "title": "Huge",
        "price": 65000,
        "privateRepos": 500,
        "stripeId": "bus-500-30",
        "audience": "For huge business",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "bus-500-2018",
        "plans_page_hidden": False,
    },
    {
        "title": "Huuge",
        "price": 120000,
        "privateRepos": 1000,
        "stripeId": "bus-1000-30",
        "audience": "For the SaaS savvy enterprise",
        "bus_features": True,
        "deprecated": True,
        "free_trial_days": 30,
        "superseded_by": "bus-1000-2018",
        "plans_page_hidden": False,
    },
    # Active plans (as of Dec 2017)
    {
        "title": "Open Source",
        "price": 0,
        "privateRepos": 0,
        "stripeId": "free",
        "audience": "Committment to FOSS",
        "bus_features": False,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "Developer",
        "price": 1500,
        "privateRepos": 5,
        "stripeId": "personal-2018",
        "audience": "Individuals",
        "bus_features": False,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "Micro",
        "price": 3000,
        "privateRepos": 10,
        "stripeId": "bus-micro-2018",
        "audience": "For startups",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "Small",
        "price": 6000,
        "privateRepos": 20,
        "stripeId": "bus-small-2018",
        "audience": "For small businesses",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "Medium",
        "price": 12500,
        "privateRepos": 50,
        "stripeId": "bus-medium-2018",
        "audience": "For normal businesses",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "Large",
        "price": 25000,
        "privateRepos": 125,
        "stripeId": "bus-large-2018",
        "audience": "For large businesses",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "Extra Large",
        "price": 45000,
        "privateRepos": 250,
        "stripeId": "bus-xlarge-2018",
        "audience": "For extra large businesses",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "XXL",
        "price": 85000,
        "privateRepos": 500,
        "stripeId": "bus-500-2018",
        "audience": "For huge business",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "XXXL",
        "price": 160000,
        "privateRepos": 1000,
        "stripeId": "bus-1000-2018",
        "audience": "For the SaaS savvy enterprise",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
    {
        "title": "XXXXL",
        "price": 310000,
        "privateRepos": 2000,
        "stripeId": "bus-2000-2018",
        "audience": "For the SaaS savvy big enterprise",
        "bus_features": True,
        "deprecated": False,
        "free_trial_days": 30,
        "superseded_by": None,
        "plans_page_hidden": False,
    },
]


def get_plan(plan_id):
    """
    Returns the plan with the given ID or None if none.
    """
    for plan in PLANS:
        if plan["stripeId"] == plan_id:
            return plan

    return None


class FakeSubscription(AttrDict):
    @classmethod
    def build(cls, data, customer):
        data = AttrDict.deep_copy(data)
        data["customer"] = customer
        return cls(data)

    def delete(self):
        self.customer.subscription = None


class FakeStripe(object):
    class Customer(AttrDict):
        FAKE_PLAN = AttrDict(
            {
                "id": "bus-small",
            }
        )

        FAKE_SUBSCRIPTION = AttrDict(
            {
                "plan": FAKE_PLAN,
                "current_period_start": timegm(datetime.utcnow().utctimetuple()),
                "current_period_end": timegm(
                    (datetime.utcnow() + timedelta(days=30)).utctimetuple()
                ),
                "trial_start": timegm(datetime.utcnow().utctimetuple()),
                "trial_end": timegm((datetime.utcnow() + timedelta(days=30)).utctimetuple()),
            }
        )

        FAKE_CARD = AttrDict(
            {
                "id": "card123",
                "name": "Joe User",
                "type": "Visa",
                "last4": "4242",
                "exp_month": 5,
                "exp_year": 2016,
            }
        )

        FAKE_CARD_LIST = AttrDict(
            {
                "data": [FAKE_CARD],
            }
        )

        ACTIVE_CUSTOMERS = {}

        @property
        def card(self):
            return self.get("new_card", None)

        @card.setter
        def card(self, card_token):
            self["new_card"] = card_token

        @property
        def plan(self):
            return self.get("new_plan", None)

        @plan.setter
        def plan(self, plan_name):
            self["new_plan"] = plan_name

        def save(self):
            if self.get("new_card", None) is not None:
                raise stripe.error.CardError(
                    "Test raising exception on set card.", self.get("new_card"), 402
                )
            if self.get("new_plan", None) is not None:
                if self.subscription is None:
                    self.subscription = FakeSubscription.build(self.FAKE_SUBSCRIPTION, self)
                self.subscription.plan.id = self.get("new_plan")

        @classmethod
        def retrieve(cls, stripe_customer_id):
            if stripe_customer_id in cls.ACTIVE_CUSTOMERS:
                cls.ACTIVE_CUSTOMERS[stripe_customer_id].pop("new_card", None)
                cls.ACTIVE_CUSTOMERS[stripe_customer_id].pop("new_plan", None)
                return cls.ACTIVE_CUSTOMERS[stripe_customer_id]
            else:
                new_customer = cls(
                    {
                        "default_card": "card123",
                        "cards": AttrDict.deep_copy(cls.FAKE_CARD_LIST),
                        "id": stripe_customer_id,
                    }
                )
                new_customer.subscription = FakeSubscription.build(
                    cls.FAKE_SUBSCRIPTION, new_customer
                )
                cls.ACTIVE_CUSTOMERS[stripe_customer_id] = new_customer
                return new_customer

    class Invoice(AttrDict):
        @staticmethod
        def list(customer, count):
            return AttrDict(
                {
                    "data": [],
                }
            )


class Billing(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        billing_type = app.config.get("BILLING_TYPE", "FakeStripe")

        if billing_type == "Stripe":
            billing = stripe
            stripe.api_key = app.config.get("STRIPE_SECRET_KEY", None)

        elif billing_type == "FakeStripe":
            billing = FakeStripe

        else:
            raise RuntimeError("Unknown billing type: %s" % billing_type)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["billing"] = billing
        return billing

    def __getattr__(self, name):
        return getattr(self.state, name, None)
