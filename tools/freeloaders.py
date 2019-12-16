from data import model
from data.database import User
from app import billing as stripe
from data.plans import get_plan


def get_private_allowed(customer):
    if not customer.stripe_id:
        return 0

    subscription = stripe.Customer.retrieve(customer.stripe_id).get("subscription", None)
    if subscription is None:
        return 0

    plan = get_plan(subscription.plan.id)
    return plan["privateRepos"]


# Find customers who have more private repositories than their plans allow
users = User.select()

usage = [
    (user.username, model.user.get_private_repo_count(user.username), get_private_allowed(user))
    for user in users
]

for username, used, allowed in usage:
    if used > allowed:
        print(("Violation: %s %s > %s" % (username, used, allowed)))
