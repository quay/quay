import io
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

from app import app

jinja_options = {
    "loader": FileSystemLoader("util"),
}

env = Environment(**jinja_options)


def renderPermissionReportToPdf(report, user, org):
    sourceHtml = renderPermissionReportToHtml(report, user, org, "pdf")
    output = io.BytesIO()
    pisaStatus = pisa.CreatePDF(sourceHtml, dest=output)
    if pisaStatus.err:
        return None

    value = output.getvalue()
    output.close()
    return value


def renderPermissionReportToHtml(report, user, org, format="html"):
    app_logo = app.config.get("ENTERPRISE_LOGO_URL", "https://quay.io/static/img/quay-logo.png")
    app_server_name = app.config.get("SERVER_HOSTNAME", "")
    url_scheme = app.config.get("PREFERRED_URL_SCHEME", "http") + "://"

    app_logo_path = url_scheme + app_server_name + app_logo if app_logo.startswith("/") else app_logo

    report_data = {
        "logo": app_logo_path,
        "permissions": report,
        "report_user": user,
        "organization_name": org,
        "server_name": app_server_name,
        "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "output_format": format,
    }

    template = env.get_template("permission_report.tmpl")
    rendered = template.render(report_data)

    return rendered
