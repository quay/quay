from app import billing
from collections import defaultdict

offset = 0


def empty_tuple():
    return (0, 0)


plan_revenue = defaultdict(empty_tuple)

batch = billing.Customer.all(count=100, offset=offset)
while batch.data:
    for cust in batch.data:
        if cust.subscription:
            sub = cust.subscription
            total_customer_revenue = sub.plan.amount * sub.quantity

            if cust.discount and cust.discount.coupon:
                coupon = cust.discount.coupon

                if coupon.percent_off:
                    total_customer_revenue *= 1 - coupon.percent_off / 100.0

                if coupon.amount_off:
                    total_customer_revenue -= coupon.amount_off

            subscribers, revenue = plan_revenue[sub.plan.id]
            plan_revenue[sub.plan.id] = (subscribers + 1, revenue + total_customer_revenue)
    offset += len(batch.data)
    batch = billing.Customer.all(count=100, offset=offset)


def format_money(total_cents):
    dollars = total_cents // 100
    cents = total_cents % 100
    return dollars, cents


total_monthly_revenue = 0
for plan_id, (subs, rev) in list(plan_revenue.items()):
    total_monthly_revenue += rev
    d, c = format_money(rev)
    print("%s: $%d.%02d(%s)" % (plan_id, d, c, subs))

d, c = format_money(total_monthly_revenue)
print("Monthly revenue: $%d.%02d" % (d, c))
