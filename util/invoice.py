from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

import io

from app import app

jinja_options = {
    "loader": FileSystemLoader("util"),
}

env = Environment(**jinja_options)


def renderInvoiceToPdf(invoice, user):
    """
    Renders a nice PDF display for the given invoice.
    """
    sourceHtml = renderInvoiceToHtml(invoice, user)
    output = io.StringIO()
    pisaStatus = pisa.CreatePDF(sourceHtml, dest=output)
    if pisaStatus.err:
        return None

    value = output.getvalue()
    output.close()
    return value


def renderInvoiceToHtml(invoice, user):
    """
    Renders a nice HTML display for the given invoice.
    """
    from endpoints.api.billing import get_invoice_fields

    def get_price(price):
        if not price:
            return "$0"

        return "$" + "{0:.2f}".format(float(price) / 100)

    def get_range(line):
        if line.period and line.period.start and line.period.end:
            return ": " + format_date(line.period.start) + " - " + format_date(line.period.end)
        return ""

    def format_date(timestamp):
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

    app_logo = app.config.get("ENTERPRISE_LOGO_URL", "https://quay.io/static/img/quay-logo.png")
    data = {
        "user": user.username,
        "invoice": invoice,
        "invoice_date": format_date(invoice.date),
        "getPrice": get_price,
        "getRange": get_range,
        "custom_fields": get_invoice_fields(user)[0],
        "logo": app_logo,
    }

    template = env.get_template("invoice.tmpl")
    rendered = template.render(data)
    return rendered
