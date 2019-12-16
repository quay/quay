import stripe
from app import app

from util.invoice import renderInvoiceToPdf

from data import model

import argparse


def sendInvoice(invoice_id):
    invoice = stripe.Invoice.retrieve(invoice_id)
    if not invoice["customer"]:
        print("No customer found")
        return

    customer_id = invoice["customer"]
    user = model.user.get_user_or_org_by_customer_id(customer_id)
    if not user:
        print("No user found for customer %s" % (customer_id))
        return

    with app.app_context():
        file_data = renderInvoiceToPdf(invoice, user)
        with open("invoice.pdf", "wb") as f:
            f.write(file_data)

        print("Invoice output as invoice.pdf")


parser = argparse.ArgumentParser(description="Generate an invoice")
parser.add_argument("invoice_id", help="The invoice ID")
args = parser.parse_args()
sendInvoice(args.invoice_id)
