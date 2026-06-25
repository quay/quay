import argparse

import stripe
from flask import Flask, current_app

from app import app
from data import model
from util.invoice import renderInvoiceToHtml
from util.useremails import send_invoice_email


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
        recipient = user.invoice_email_address or user.get_contact_email()
        if not recipient:
            print("No recipient email found for customer %s" % customer_id)
            return
        send_invoice_email(recipient, invoice_html)
        print("Invoice sent to %s" % recipient)


parser = argparse.ArgumentParser(description="Email an invoice")
parser.add_argument("invoice_id", help="The invoice ID")
args = parser.parse_args()
sendInvoice(args.invoice_id)
