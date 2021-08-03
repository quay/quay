import stripe
from app import app

from util.invoice import renderInvoiceToHtml
from util.useremails import send_invoice_email

from data import model

import argparse

from flask import Flask, current_app


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
        invoice_html = renderInvoiceToHtml(invoice, user)
        send_invoice_email(user.invoice_email_address or user.email, invoice_html)
        print("Invoice sent to %s" % (user.invoice_email_address or user.email))


parser = argparse.ArgumentParser(description="Email an invoice")
parser.add_argument("invoice_id", help="The invoice ID")
args = parser.parse_args()
sendInvoice(args.invoice_id)
