import logging

from flask import request, make_response, Blueprint

from app import billing as stripe, app
from data import model
from data.database import RepositoryState
from auth.decorators import process_auth
from auth.permissions import ModifyRepositoryPermission
from util.invoice import renderInvoiceToHtml
from util.useremails import send_invoice_email, send_subscription_change, send_payment_failed
from util.http import abort
from buildtrigger.basehandler import BuildTriggerHandler
from buildtrigger.triggerutil import (
    ValidationRequestException,
    SkipRequestException,
    InvalidPayloadException,
)
from endpoints.building import (
    start_build,
    MaximumBuildsQueuedException,
    BuildTriggerDisabledException,
)


logger = logging.getLogger(__name__)

webhooks = Blueprint("webhooks", __name__)


@webhooks.route("/stripe", methods=["POST"])
def stripe_webhook():
    request_data = request.get_json()
    logger.debug("Stripe webhook call: %s", request_data)

    customer_id = request_data.get("data", {}).get("object", {}).get("customer", None)
    namespace = model.user.get_user_or_org_by_customer_id(customer_id) if customer_id else None

    event_type = request_data["type"] if "type" in request_data else None
    if event_type == "charge.succeeded":
        invoice_id = request_data["data"]["object"]["invoice"]

        namespace = model.user.get_user_or_org_by_customer_id(customer_id) if customer_id else None
        if namespace:
            # Increase the namespace's build allowance, since we had a successful charge.
            build_maximum = app.config.get("BILLED_NAMESPACE_MAXIMUM_BUILD_COUNT")
            if build_maximum is not None:
                model.user.increase_maximum_build_count(namespace, build_maximum)

            if namespace.invoice_email:
                # Lookup the invoice.
                invoice = stripe.Invoice.retrieve(invoice_id)
                if invoice:
                    invoice_html = renderInvoiceToHtml(invoice, namespace)
                    send_invoice_email(
                        namespace.invoice_email_address or namespace.email, invoice_html
                    )

    elif event_type.startswith("customer.subscription."):
        cust_email = namespace.email if namespace is not None else "unknown@domain.com"
        quay_username = namespace.username if namespace is not None else "unknown"

        change_type = ""
        if event_type.endswith(".deleted"):
            plan_id = request_data["data"]["object"]["plan"]["id"]
            requested = bool(request_data.get("request"))
            if requested:
                change_type = "canceled %s" % plan_id
                send_subscription_change(change_type, customer_id, cust_email, quay_username)
        elif event_type.endswith(".created"):
            plan_id = request_data["data"]["object"]["plan"]["id"]
            change_type = "subscribed %s" % plan_id
            send_subscription_change(change_type, customer_id, cust_email, quay_username)
        elif event_type.endswith(".updated"):
            if "previous_attributes" in request_data["data"]:
                if "plan" in request_data["data"]["previous_attributes"]:
                    old_plan = request_data["data"]["previous_attributes"]["plan"]["id"]
                    new_plan = request_data["data"]["object"]["plan"]["id"]
                    change_type = "switched %s -> %s" % (old_plan, new_plan)
                    send_subscription_change(change_type, customer_id, cust_email, quay_username)

    elif event_type == "invoice.payment_failed":
        if namespace:
            send_payment_failed(namespace.email, namespace.username)

    return make_response("Okay")


@webhooks.route("/push/<repopath:repository>/trigger/<trigger_uuid>", methods=["POST"])
@webhooks.route("/push/trigger/<trigger_uuid>", methods=["POST"], defaults={"repository": ""})
@process_auth
def build_trigger_webhook(trigger_uuid, **kwargs):
    logger.debug("Webhook received with uuid %s", trigger_uuid)

    try:
        trigger = model.build.get_build_trigger(trigger_uuid)
    except model.InvalidBuildTriggerException:
        # It is ok to return 404 here, since letting an attacker know that a trigger UUID is valid
        # doesn't leak anything
        abort(404)

    # Ensure we are not currently in read-only mode.
    if app.config.get("REGISTRY_STATE", "normal") == "readonly":
        abort(503, "System is currently in read-only mode")

    # Ensure the trigger has permission.
    namespace = trigger.repository.namespace_user.username
    repository = trigger.repository.name
    if ModifyRepositoryPermission(namespace, repository).can():
        handler = BuildTriggerHandler.get_handler(trigger)

        if trigger.repository.kind.name != "image":
            abort(501, "Build triggers cannot be invoked on application repositories")

        if trigger.repository.state != RepositoryState.NORMAL:
            abort(503, "Repository is currently in read only or mirror mode")

        logger.debug("Passing webhook request to handler %s", handler)
        try:
            prepared = handler.handle_trigger_request(request)
        except ValidationRequestException:
            logger.debug("Handler reported a validation exception: %s", handler)
            # This was just a validation request, we don't need to build anything
            return make_response("Okay")
        except SkipRequestException:
            logger.debug("Handler reported to skip the build: %s", handler)
            # The build was requested to be skipped
            return make_response("Okay")
        except InvalidPayloadException as ipe:
            logger.exception("Invalid payload")
            # The payload was malformed
            abort(400, message=str(ipe))

        pull_robot_name = model.build.get_pull_robot_name(trigger)
        repo = model.repository.get_repository(namespace, repository)
        try:
            start_build(repo, prepared, pull_robot_name=pull_robot_name)
        except MaximumBuildsQueuedException:
            abort(429, message="Maximum queued build rate exceeded.")
        except BuildTriggerDisabledException:
            logger.debug("Build trigger %s is disabled", trigger_uuid)
            abort(
                400,
                message="This build trigger is currently disabled. Please re-enable to continue.",
            )

        return make_response("Okay")

    abort(403)
