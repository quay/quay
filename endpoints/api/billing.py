"""
Billing information, subscriptions, and plan information.
"""

import stripe

from flask import request
from app import billing
from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    validate_json_request,
    log_action,
    related_user_resource,
    internal_only,
    require_user_admin,
    show_if,
    path_param,
    require_scope,
    abort,
)
from endpoints.exception import Unauthorized, NotFound
from endpoints.api.subscribe import subscribe, subscription_view
from auth.permissions import AdministerOrganizationPermission
from auth.auth_context import get_authenticated_user
from auth import scopes
from data import model
from data.billing import PLANS, get_plan

import features
import uuid
import json


def get_namespace_plan(namespace):
    """
    Returns the plan of the given namespace.
    """
    namespace_user = model.user.get_namespace_user(namespace)
    if namespace_user is None:
        return None

    if not namespace_user.stripe_id:
        return None

    # Ask Stripe for the subscribed plan.
    # TODO: Can we cache this or make it faster somehow?
    try:
        cus = billing.Customer.retrieve(namespace_user.stripe_id)
    except stripe.error.APIConnectionError:
        abort(503, message="Cannot contact Stripe")

    if not cus.subscription:
        return None

    return get_plan(cus.subscription.plan.id)


def lookup_allowed_private_repos(namespace):
    """
    Returns false if the given namespace has used its allotment of private repositories.
    """
    current_plan = get_namespace_plan(namespace)
    if current_plan is None:
        return False

    # Find the number of private repositories used by the namespace and compare it to the
    # plan subscribed.
    private_repos = model.user.get_private_repo_count(namespace)

    return private_repos < current_plan["privateRepos"]


def carderror_response(e):
    return {"carderror": str(e)}, 402


def get_card(user):
    card_info = {"is_valid": False}

    if user.stripe_id:
        try:
            cus = billing.Customer.retrieve(user.stripe_id)
        except stripe.error.APIConnectionError as e:
            abort(503, message="Cannot contact Stripe")

        if cus and cus.default_card:
            # Find the default card.
            default_card = None
            for card in cus.cards.data:
                if card.id == cus.default_card:
                    default_card = card
                    break

            if default_card:
                card_info = {
                    "owner": default_card.name,
                    "type": default_card.type,
                    "last4": default_card.last4,
                    "exp_month": default_card.exp_month,
                    "exp_year": default_card.exp_year,
                }

    return {"card": card_info}


def set_card(user, token):
    if user.stripe_id:
        try:
            cus = billing.Customer.retrieve(user.stripe_id)
        except stripe.error.APIConnectionError as e:
            abort(503, message="Cannot contact Stripe")

        if cus:
            try:
                cus.card = token
                cus.save()
            except stripe.error.CardError as exc:
                return carderror_response(exc)
            except stripe.error.InvalidRequestError as exc:
                return carderror_response(exc)
            except stripe.error.APIConnectionError as e:
                return carderror_response(e)

    return get_card(user)


def get_invoices(customer_id):
    def invoice_view(i):
        return {
            "id": i.id,
            "date": i.date,
            "period_start": i.period_start,
            "period_end": i.period_end,
            "paid": i.paid,
            "amount_due": i.amount_due,
            "next_payment_attempt": i.next_payment_attempt,
            "attempted": i.attempted,
            "closed": i.closed,
            "total": i.total,
            "plan": i.lines.data[0].plan.id if i.lines.data[0].plan else None,
        }

    try:
        invoices = billing.Invoice.list(customer=customer_id, count=12)
    except stripe.error.APIConnectionError as e:
        abort(503, message="Cannot contact Stripe")

    return {"invoices": [invoice_view(i) for i in invoices.data]}


def get_invoice_fields(user):
    try:
        cus = billing.Customer.retrieve(user.stripe_id)
    except stripe.error.APIConnectionError:
        abort(503, message="Cannot contact Stripe")

    if not "metadata" in cus:
        cus.metadata = {}

    return json.loads(cus.metadata.get("invoice_fields") or "[]"), cus


def create_billing_invoice_field(user, title, value):
    new_field = {"uuid": str(uuid.uuid4()).split("-")[0], "title": title, "value": value}

    invoice_fields, cus = get_invoice_fields(user)
    invoice_fields.append(new_field)

    if not "metadata" in cus:
        cus.metadata = {}

    cus.metadata["invoice_fields"] = json.dumps(invoice_fields)
    cus.save()
    return new_field


def delete_billing_invoice_field(user, field_uuid):
    invoice_fields, cus = get_invoice_fields(user)
    invoice_fields = [field for field in invoice_fields if not field["uuid"] == field_uuid]

    if not "metadata" in cus:
        cus.metadata = {}

    cus.metadata["invoice_fields"] = json.dumps(invoice_fields)
    cus.save()
    return True


@resource("/v1/plans/")
@show_if(features.BILLING)
class ListPlans(ApiResource):
    """
    Resource for listing the available plans.
    """

    @nickname("listPlans")
    def get(self):
        """
        List the avaialble plans.
        """
        return {
            "plans": PLANS,
        }


@resource("/v1/user/card")
@internal_only
@show_if(features.BILLING)
class UserCard(ApiResource):
    """
    Resource for managing a user's credit card.
    """

    schemas = {
        "UserCard": {
            "id": "UserCard",
            "type": "object",
            "description": "Description of a user card",
            "required": ["token",],
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Stripe token that is generated by stripe checkout.js",
                },
            },
        },
    }

    @require_user_admin
    @nickname("getUserCard")
    def get(self):
        """
        Get the user's credit card.
        """
        user = get_authenticated_user()
        return get_card(user)

    @require_user_admin
    @nickname("setUserCard")
    @validate_json_request("UserCard")
    def post(self):
        """
        Update the user's credit card.
        """
        user = get_authenticated_user()
        token = request.get_json()["token"]
        response = set_card(user, token)
        log_action("account_change_cc", user.username)
        return response


@resource("/v1/organization/<orgname>/card")
@path_param("orgname", "The name of the organization")
@internal_only
@related_user_resource(UserCard)
@show_if(features.BILLING)
class OrganizationCard(ApiResource):
    """
    Resource for managing an organization's credit card.
    """

    schemas = {
        "OrgCard": {
            "id": "OrgCard",
            "type": "object",
            "description": "Description of a user card",
            "required": ["token",],
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Stripe token that is generated by stripe checkout.js",
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrgCard")
    def get(self, orgname):
        """
        Get the organization's credit card.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            return get_card(organization)

        raise Unauthorized()

    @nickname("setOrgCard")
    @validate_json_request("OrgCard")
    def post(self, orgname):
        """
        Update the orgnaization's credit card.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            token = request.get_json()["token"]
            response = set_card(organization, token)
            log_action("account_change_cc", orgname)
            return response

        raise Unauthorized()


@resource("/v1/user/plan")
@internal_only
@show_if(features.BILLING)
class UserPlan(ApiResource):
    """
    Resource for managing a user's subscription.
    """

    schemas = {
        "UserSubscription": {
            "id": "UserSubscription",
            "type": "object",
            "description": "Description of a user card",
            "required": ["plan",],
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Stripe token that is generated by stripe checkout.js",
                },
                "plan": {
                    "type": "string",
                    "description": "Plan name to which the user wants to subscribe",
                },
            },
        },
    }

    @require_user_admin
    @nickname("updateUserSubscription")
    @validate_json_request("UserSubscription")
    def put(self):
        """
        Create or update the user's subscription.
        """
        request_data = request.get_json()
        plan = request_data["plan"]
        token = request_data["token"] if "token" in request_data else None
        user = get_authenticated_user()
        return subscribe(user, plan, token, False)  # Business features not required

    @require_user_admin
    @nickname("getUserSubscription")
    def get(self):
        """
        Fetch any existing subscription for the user.
        """
        cus = None
        user = get_authenticated_user()
        private_repos = model.user.get_private_repo_count(user.username)

        if user.stripe_id:
            try:
                cus = billing.Customer.retrieve(user.stripe_id)
            except stripe.error.APIConnectionError as e:
                abort(503, message="Cannot contact Stripe")

            if cus.subscription:
                return subscription_view(cus.subscription, private_repos)

        return {
            "hasSubscription": False,
            "isExistingCustomer": cus is not None,
            "plan": "free",
            "usedPrivateRepos": private_repos,
        }


@resource("/v1/organization/<orgname>/plan")
@path_param("orgname", "The name of the organization")
@internal_only
@related_user_resource(UserPlan)
@show_if(features.BILLING)
class OrganizationPlan(ApiResource):
    """
    Resource for managing a org's subscription.
    """

    schemas = {
        "OrgSubscription": {
            "id": "OrgSubscription",
            "type": "object",
            "description": "Description of a user card",
            "required": ["plan",],
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Stripe token that is generated by stripe checkout.js",
                },
                "plan": {
                    "type": "string",
                    "description": "Plan name to which the user wants to subscribe",
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrgSubscription")
    @validate_json_request("OrgSubscription")
    def put(self, orgname):
        """
        Create or update the org's subscription.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            request_data = request.get_json()
            plan = request_data["plan"]
            token = request_data["token"] if "token" in request_data else None
            organization = model.organization.get_organization(orgname)
            return subscribe(organization, plan, token, True)  # Business plan required

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrgSubscription")
    def get(self, orgname):
        """
        Fetch any existing subscription for the org.
        """
        cus = None
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            private_repos = model.user.get_private_repo_count(orgname)
            organization = model.organization.get_organization(orgname)
            if organization.stripe_id:
                try:
                    cus = billing.Customer.retrieve(organization.stripe_id)
                except stripe.error.APIConnectionError as e:
                    abort(503, message="Cannot contact Stripe")

                if cus.subscription:
                    return subscription_view(cus.subscription, private_repos)

            return {
                "hasSubscription": False,
                "isExistingCustomer": cus is not None,
                "plan": "free",
                "usedPrivateRepos": private_repos,
            }

        raise Unauthorized()


@resource("/v1/user/invoices")
@internal_only
@show_if(features.BILLING)
class UserInvoiceList(ApiResource):
    """
    Resource for listing a user's invoices.
    """

    @require_user_admin
    @nickname("listUserInvoices")
    def get(self):
        """
        List the invoices for the current user.
        """
        user = get_authenticated_user()
        if not user.stripe_id:
            raise NotFound()

        return get_invoices(user.stripe_id)


@resource("/v1/organization/<orgname>/invoices")
@path_param("orgname", "The name of the organization")
@related_user_resource(UserInvoiceList)
@show_if(features.BILLING)
class OrganizationInvoiceList(ApiResource):
    """
    Resource for listing an orgnaization's invoices.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("listOrgInvoices")
    def get(self, orgname):
        """
        List the invoices for the specified orgnaization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            if not organization.stripe_id:
                raise NotFound()

            return get_invoices(organization.stripe_id)

        raise Unauthorized()


@resource("/v1/user/invoice/fields")
@internal_only
@show_if(features.BILLING)
class UserInvoiceFieldList(ApiResource):
    """
    Resource for listing and creating a user's custom invoice fields.
    """

    schemas = {
        "InvoiceField": {
            "id": "InvoiceField",
            "type": "object",
            "description": "Description of an invoice field",
            "required": ["title", "value"],
            "properties": {
                "title": {"type": "string", "description": "The title of the field being added",},
                "value": {"type": "string", "description": "The value of the field being added",},
            },
        },
    }

    @require_user_admin
    @nickname("listUserInvoiceFields")
    def get(self):
        """
        List the invoice fields for the current user.
        """
        user = get_authenticated_user()
        if not user.stripe_id:
            raise NotFound()

        return {"fields": get_invoice_fields(user)[0]}

    @require_user_admin
    @nickname("createUserInvoiceField")
    @validate_json_request("InvoiceField")
    def post(self):
        """
        Creates a new invoice field.
        """
        user = get_authenticated_user()
        if not user.stripe_id:
            raise NotFound()

        data = request.get_json()
        created_field = create_billing_invoice_field(user, data["title"], data["value"])
        return created_field


@resource("/v1/user/invoice/field/<field_uuid>")
@internal_only
@show_if(features.BILLING)
class UserInvoiceField(ApiResource):
    """
    Resource for deleting a user's custom invoice fields.
    """

    @require_user_admin
    @nickname("deleteUserInvoiceField")
    def delete(self, field_uuid):
        """
        Deletes the invoice field for the current user.
        """
        user = get_authenticated_user()
        if not user.stripe_id:
            raise NotFound()

        result = delete_billing_invoice_field(user, field_uuid)
        if not result:
            abort(404)

        return "Okay", 201


@resource("/v1/organization/<orgname>/invoice/fields")
@path_param("orgname", "The name of the organization")
@related_user_resource(UserInvoiceFieldList)
@internal_only
@show_if(features.BILLING)
class OrganizationInvoiceFieldList(ApiResource):
    """
    Resource for listing and creating an organization's custom invoice fields.
    """

    schemas = {
        "InvoiceField": {
            "id": "InvoiceField",
            "type": "object",
            "description": "Description of an invoice field",
            "required": ["title", "value"],
            "properties": {
                "title": {"type": "string", "description": "The title of the field being added",},
                "value": {"type": "string", "description": "The value of the field being added",},
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("listOrgInvoiceFields")
    def get(self, orgname):
        """
        List the invoice fields for the organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            if not organization.stripe_id:
                raise NotFound()

            return {"fields": get_invoice_fields(organization)[0]}

        abort(403)

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrgInvoiceField")
    @validate_json_request("InvoiceField")
    def post(self, orgname):
        """
        Creates a new invoice field.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            if not organization.stripe_id:
                raise NotFound()

            data = request.get_json()
            created_field = create_billing_invoice_field(organization, data["title"], data["value"])
            return created_field

        abort(403)


@resource("/v1/organization/<orgname>/invoice/field/<field_uuid>")
@path_param("orgname", "The name of the organization")
@related_user_resource(UserInvoiceField)
@internal_only
@show_if(features.BILLING)
class OrganizationInvoiceField(ApiResource):
    """
    Resource for deleting an organization's custom invoice fields.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrgInvoiceField")
    def delete(self, orgname, field_uuid):
        """
        Deletes the invoice field for the current user.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            if not organization.stripe_id:
                raise NotFound()

            result = delete_billing_invoice_field(organization, field_uuid)
            if not result:
                abort(404)

            return "Okay", 201

        abort(403)
