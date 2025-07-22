"""
Billing information, subscriptions, and plan information.
"""
import datetime
import json
import time
import uuid

import stripe
from flask import request

import features
from app import app, billing, marketplace_subscriptions, marketplace_users
from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.permissions import AdministerOrganizationPermission
from data import model
from data.billing import PLANS, get_plan, get_plan_using_rh_sku
from data.model import InvalidOrganizationException, organization_skus
from endpoints.api import (
    ApiResource,
    abort,
    internal_only,
    log_action,
    nickname,
    path_param,
    related_user_resource,
    require_scope,
    require_user_admin,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.api.subscribe import (
    change_subscription,
    check_repository_usage,
    connection_response,
    get_price,
    subscription_view,
)
from endpoints.exception import InvalidRequest, NotFound, Unauthorized
from util.request import get_request_ip

MILLISECONDS_IN_SECONDS = 1000


def check_internal_api_for_subscription(namespace_user):
    """
    Returns subscription from RH marketplace.
    None returned if no subscription is found.
    """
    plans = []
    if namespace_user.organization:
        query = organization_skus.get_org_subscriptions(namespace_user.id)
        org_subscriptions = list(query.dicts()) if query is not None else []
        for subscription in org_subscriptions:
            quantity = 1 if subscription.get("quantity") is None else subscription["quantity"]
            subscription_id = subscription["subscription_id"]
            subscription_details = marketplace_subscriptions.get_subscription_details(
                subscription_id
            )
            sku = subscription_details["sku"]
            expiration = subscription_details["expiration_date"]
            terminated = subscription_details["terminated_date"]
            now_ms = time.time() * 1000
            if expiration < now_ms or (terminated is not None and terminated < now_ms):
                organization_skus.remove_subscription_from_org(namespace_user.id, subscription_id)
                continue
            for x in range(quantity):
                plans.append(get_plan_using_rh_sku(sku))
        pass
    else:
        user_account_numbers = marketplace_users.get_account_number(namespace_user)
        if user_account_numbers:
            plans = []
            for user_account_number in user_account_numbers:
                plans += marketplace_subscriptions.get_list_of_subscriptions(
                    user_account_number, filter_out_org_bindings=True, convert_to_stripe_plans=True
                )
    return plans


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
    repos_allowed = 0
    current_plan = get_namespace_plan(namespace)

    if features.RH_MARKETPLACE:
        namespace_user = model.user.get_namespace_user(namespace)

        subscriptions = check_internal_api_for_subscription(namespace_user)
        for subscription in subscriptions:
            if subscription is not None:
                repos_allowed += subscription["privateRepos"]

    # Find the number of private repositories used by the namespace and compare it to the
    # plan subscribed.
    if current_plan is not None:
        repos_allowed += current_plan["privateRepos"]

    private_repos = model.user.get_private_repo_count(namespace)
    return private_repos < repos_allowed


def carderror_response(e):
    return {"carderror": str(e)}, 402


def get_card(user):
    card_info = {"is_valid": False}

    if user.stripe_id:
        try:
            cus = billing.Customer.retrieve(user.stripe_id)
        except stripe.error.APIConnectionError as e:
            abort(503, message="Cannot contact Stripe")

        if cus:
            if cus.subscription and cus.subscription.default_payment_method:
                payment_method = billing.PaymentMethod.retrieve(
                    cus.subscription.default_payment_method
                )

                if payment_method.card:
                    default_card = payment_method.card
                    card_info = {
                        "owner": payment_method.billing_details.name,
                        "type": payment_method.type,
                        "last4": default_card.last4,
                        "exp_month": default_card.exp_month,
                        "exp_year": default_card.exp_year,
                    }

            # Stripe pre-paymentmethod api
            # Ref: https://stripe.com/blog/payment-api-design
            elif cus.default_card:
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
            "required": ["success_url", "cancel_url"],
            "properties": {
                "success_url": {
                    "type": "string",
                    "description": "Redirect url after successful checkout",
                },
                "cancel_url": {
                    "type": "string",
                    "description": "Redirect url after cancelled checkout",
                },
            },
        },
    }

    @require_user_admin()
    @nickname("getUserCard")
    def get(self):
        """
        Get the user's credit card.
        """
        user = get_authenticated_user()
        return get_card(user)

    @require_user_admin()
    @nickname("setUserCard")
    @validate_json_request("UserCard")
    def post(self):
        """
        Update the user's credit card.
        """
        user = get_authenticated_user()
        assert user.stripe_id

        request_data = request.get_json()
        success_url = request_data["success_url"]
        cancel_url = request_data["cancel_url"]

        try:
            cus = billing.Customer.retrieve(user.stripe_id)
        except stripe.error.APIConnectionError as e:
            abort(503, message="Cannot contact Stripe")

        if not cus:
            raise InvalidRequest("Invalid Stripe customer")

        if not cus.subscription:
            raise InvalidRequest("Invalid Stripe subscription")

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="setup",
                customer=user.stripe_id,
                setup_intent_data={
                    "metadata": {
                        "kind": "account_change_cc",
                        "namespace": user.username,
                        "performer": user.username,
                        "ip": get_request_ip(),
                        "subscription_id": cus.subscription.id,
                    },
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )

            return checkout_session
        except stripe.error.APIConnectionError as se:
            abort(503, message="Cannot contact Stripe: %s" % se)
        except Exception as e:
            abort(500, message=str(e))


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
            "description": "Description of an Organization card",
            "required": ["success_url", "cancel_url"],
            "properties": {
                "success_url": {
                    "type": "string",
                    "description": "Redirect url after successful checkout",
                },
                "cancel_url": {
                    "type": "string",
                    "description": "Redirect url after cancelled checkout",
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
            assert organization.stripe_id

            request_data = request.get_json()
            success_url = request_data["success_url"]
            cancel_url = request_data["cancel_url"]

            try:
                cus = billing.Customer.retrieve(organization.stripe_id)
            except stripe.error.APIConnectionError as e:
                abort(503, message="Cannot contact Stripe")

            if not cus:
                raise InvalidRequest("Invalid Stripe customer")

            if not cus.subscription:
                raise InvalidRequest("Invalid Stripe subscription")

            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    mode="setup",
                    customer=organization.stripe_id,
                    setup_intent_data={
                        "metadata": {
                            "kind": "account_change_cc",
                            "namespace": organization.username,
                            "performer": get_authenticated_user().username,
                            "ip": get_request_ip(),
                            "subscription_id": cus.subscription.id,
                        },
                    },
                    success_url=success_url,
                    cancel_url=cancel_url,
                )

                return checkout_session
            except stripe.error.APIConnectionError as se:
                abort(503, message="Cannot contact Stripe: %s" % se)
            except Exception as e:
                abort(500, message=str(e))

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
            "required": ["plan"],
            "properties": {
                "plan": {
                    "type": "string",
                    "description": "Plan name to which the user wants to subscribe",
                },
                "success_url": {
                    "type": "string",
                    "description": "Redirect url after successful checkout",
                },
                "cancel_url": {
                    "type": "string",
                    "description": "Redirect url after cancelled checkout",
                },
            },
        },
    }

    @require_user_admin()
    @nickname("createUserSubscription")
    @validate_json_request("UserSubscription")
    def post(self):
        """
        Create the user's subscription. Returns a Stripe checkout session.
        """
        request_data = request.get_json()
        plan = request_data["plan"]
        success_url = request_data.get("success_url")
        cancel_url = request_data.get("cancel_url")

        if not success_url or not cancel_url:
            raise InvalidRequest()

        user = get_authenticated_user()
        if not user.stripe_id:
            try:
                cus = billing.Customer.create(
                    email=user.email,
                )
                user.stripe_id = cus.id
                user.save()
            except stripe.error.APIConnectionError as e:
                return connection_response(e)

        try:
            price = get_price(plan, False)
            if not price:
                abort(404, message="Plan not found")

            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        "price": price["stripeId"],
                        "quantity": 1,
                    },
                ],
                customer=user.stripe_id,
                subscription_data={
                    "metadata": {
                        "kind": "account_change_plan",
                        "namespace": user.username,
                        "performer": user.username,
                        "ip": get_request_ip(),
                        "plan": price["stripeId"],
                    }
                },
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return checkout_session
        except stripe.error.APIConnectionError as e:
            abort(503, message="Cannot contact Stripe")
        except Exception as e:
            abort(500, message=str(e))

    @require_user_admin()
    @nickname("updateUserSubscription")
    @validate_json_request("UserSubscription")
    def put(self):
        """
        Update the user's existing subscription.
        """
        request_data = request.get_json()
        plan = request_data["plan"]

        user = get_authenticated_user()
        if not user.stripe_id:
            raise InvalidRequest()

        price = get_price(plan, False)
        if not price:
            abort(404, message="Plan not found")

        return change_subscription(user, price)

    @require_user_admin()
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
            "required": ["plan"],
            "properties": {
                "plan": {
                    "type": "string",
                    "description": "Plan name to which the user wants to subscribe",
                },
                "success_url": {
                    "type": "string",
                    "description": "Redirect url after successful checkout",
                },
                "cancel_url": {
                    "type": "string",
                    "description": "Redirect url after cancelled checkout",
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrgSubscription")
    @validate_json_request("OrgSubscription")
    def post(self, orgname):
        """
        Create the org's subscription. Returns a Stripe checkout session.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            request_data = request.get_json()
            plan = request_data["plan"]
            success_url = request_data.get("success_url")
            cancel_url = request_data.get("cancel_url")

            if not success_url or not cancel_url:
                raise InvalidRequest()

            organization = model.organization.get_organization(orgname)
            if not organization.stripe_id:
                try:
                    cus = billing.Customer.create(
                        email=organization.email,
                    )
                    organization.stripe_id = cus.id
                    organization.save()
                except stripe.error.APIConnectionError as e:
                    return connection_response(e)

            try:
                price = get_price(plan, True)
                if not price:
                    abort(404, message="Plan not found")

                checkout_session = stripe.checkout.Session.create(
                    line_items=[
                        {
                            "price": price["stripeId"],
                            "quantity": 1,
                        },
                    ],
                    customer=organization.stripe_id,
                    subscription_data={
                        "metadata": {
                            "kind": "account_change_plan",
                            "namespace": organization.username,
                            "performer": get_authenticated_user().username,
                            "ip": get_request_ip(),
                            "plan": price["stripeId"],
                            "trial_period_days": price["free_trial_days"],
                        },
                    },
                    mode="subscription",
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
                return checkout_session
            except stripe.error.APIConnectionError as e:
                abort(503, message="Cannot contact Stripe")
            except Exception as e:
                abort(500, message=str(e))

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrgSubscription")
    @validate_json_request("OrgSubscription")
    def put(self, orgname):
        """
        Update the org's subscription.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            request_data = request.get_json()
            plan = request_data["plan"]

            organization = model.organization.get_organization(orgname)
            if not organization.stripe_id:
                raise InvalidRequest()

            price = get_price(plan, True)
            if not price:
                abort(404, message="Plan not found")

            return change_subscription(organization, price)

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

    @require_user_admin()
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
                "title": {
                    "type": "string",
                    "description": "The title of the field being added",
                },
                "value": {
                    "type": "string",
                    "description": "The value of the field being added",
                },
            },
        },
    }

    @require_user_admin()
    @nickname("listUserInvoiceFields")
    def get(self):
        """
        List the invoice fields for the current user.
        """
        user = get_authenticated_user()
        if not user.stripe_id:
            raise NotFound()

        return {"fields": get_invoice_fields(user)[0]}

    @require_user_admin()
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

    @require_user_admin()
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
                "title": {
                    "type": "string",
                    "description": "The title of the field being added",
                },
                "value": {
                    "type": "string",
                    "description": "The value of the field being added",
                },
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


@resource("/v1/organization/<orgname>/marketplace")
@path_param("orgname", "The name of the organization")
@show_if(features.BILLING)
class OrganizationRhSku(ApiResource):
    """
    Resource for managing an organization's RH SKU
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("listOrgSkus")
    def get(self, orgname):
        """
        Get sku assigned to org
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            query = model.organization_skus.get_org_subscriptions(organization.id)

            if query:
                subscriptions = list(query.dicts())
                for subscription in subscriptions:
                    subscription_details = marketplace_subscriptions.get_subscription_details(
                        subscription["subscription_id"]
                    )
                    now_ms = time.time() * 1000
                    expired_at = subscription_details["expiration_date"]
                    terminated_at = subscription_details["terminated_date"]
                    if expired_at < now_ms or (
                        terminated_at is not None and terminated_at < now_ms
                    ):
                        model.organization_skus.remove_subscription_from_org(
                            organization.id, subscription["subscription_id"]
                        )
                        continue
                    subscription["sku"] = subscription_details["sku"]
                    subscription["metadata"] = get_plan_using_rh_sku(subscription_details["sku"])
                    if subscription.get("quantity") is None:
                        subscription["quantity"] = 1
                return subscriptions
            else:
                return []
        abort(401)

    @require_scope(scopes.ORG_ADMIN)
    @nickname("bindSkuToOrg")
    def post(self, orgname):
        """
        Assigns a sku to an org
        """
        permission = AdministerOrganizationPermission(orgname)
        request_data = request.get_json()
        organization = model.organization.get_organization(orgname)
        subscriptions = request_data["subscriptions"]
        if permission.can():
            for subscription in subscriptions:
                subscription_id = subscription.get("subscription_id")
                if subscription_id is None:
                    break
                user = get_authenticated_user()
                account_numbers = marketplace_users.get_account_number(user)
                user_available_subscriptions = []
                for account_number in account_numbers:
                    user_available_subscriptions += (
                        marketplace_subscriptions.get_list_of_subscriptions(
                            account_number, filter_out_org_bindings=True
                        )
                    )

                if subscriptions is None:
                    abort(401, message="no valid subscriptions present")

                user_subs = {sub["id"]: sub for sub in user_available_subscriptions}
                if int(subscription_id) in user_subs.keys():
                    # Check if the sku is being split
                    quantity = subscription.get("quantity")
                    base_quantity = user_subs.get(subscription_id).get("quantity", 1)
                    sku = user_subs.get(subscription_id).get("sku")

                    if quantity is not None:
                        if sku != "MW02702" and quantity != base_quantity:
                            abort(403, message="cannot split a non-MW02702 sku")
                        if quantity > base_quantity:
                            abort(400, message="quantity cannot exceed available amount")
                    else:
                        quantity = base_quantity

                    try:
                        model.organization_skus.bind_subscription_to_org(
                            user_id=user.id,
                            subscription_id=subscription_id,
                            org_id=organization.id,
                            quantity=quantity,
                        )
                    except model.OrgSubscriptionBindingAlreadyExists:
                        abort(400, message="subscription is already bound to an org")
                else:
                    abort(
                        401,
                        message=f"subscription {subscription_id} does not belong to {user.username}",
                    )

            return "Okay", 201

        abort(401)


@resource("/v1/organization/<orgname>/marketplace/batchremove")
@path_param("orgname", "The name of the organization")
@show_if(features.BILLING)
class OrganizationRhSkuBatchRemoval(ApiResource):
    @require_scope(scopes.ORG_ADMIN)
    @nickname("batchRemoveSku")
    def post(self, orgname):
        """
        Batch remove skus from org
        """
        permission = AdministerOrganizationPermission(orgname)
        request_data = request.get_json()
        subscriptions = request_data["subscriptions"]
        if permission.can():
            try:
                organization = model.organization.get_organization(orgname)
            except InvalidOrganizationException:
                return ("Organization not valid", 400)
            for subscription in subscriptions:
                subscription_id = int(subscription.get("subscription_id"))
                if subscription_id is None:
                    break
                model.organization_skus.remove_subscription_from_org(
                    organization.id, subscription_id
                )
            return ("Deleted", 204)
        abort(401)


@resource("/v1/organization/<orgname>/marketplace/<subscription_id>")
@path_param("orgname", "The name of the organization")
@path_param("subscription_id", "Marketplace subscription id")
@show_if(features.BILLING)
class OrganizationRhSkuSubscriptionField(ApiResource):
    """
    Resource for removing RH skus from an organization
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("removeSkuFromOrg")
    def delete(self, orgname, subscription_id):
        """
        Remove sku from an org
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                organization = model.organization.get_organization(orgname)
            except InvalidOrganizationException:
                return ("Organization not valid", 400)

            model.organization_skus.remove_subscription_from_org(organization.id, subscription_id)
            return ("Deleted", 204)
        abort(401)


@resource("/v1/user/marketplace")
@show_if(features.RH_MARKETPLACE)
class UserSkuList(ApiResource):
    """
    Resource for listing a user's RH skus
    bound to an org
    """

    @require_user_admin()
    @nickname("getUserMarketplaceSubscriptions")
    def get(self):
        """
        List the invoices for the current user.
        """
        user = get_authenticated_user()
        account_numbers = marketplace_users.get_account_number(user)
        if not account_numbers:
            raise NotFound()

        user_subscriptions = []
        for account_number in account_numbers:
            user_subscriptions += marketplace_subscriptions.get_list_of_subscriptions(
                account_number
            )

        child_subscriptions = []
        for subscription in user_subscriptions:
            bound_to_org, bindings = organization_skus.subscription_bound_to_org(subscription["id"])
            # fill in information for whether a subscription is bound to an org
            metadata = get_plan_using_rh_sku(subscription["sku"])
            if bound_to_org:
                # special case for MW02702, which can be split across orgs
                if subscription["sku"] == "MW02702":
                    number_of_bindings = 0
                    for binding in bindings:
                        # for each bound org, create a new subscription to add to
                        # the response body
                        child_subscription = subscription.copy()
                        child_subscription["quantity"] = binding["quantity"]
                        child_subscription[
                            "assigned_to_org"
                        ] = model.organization.get_organization_by_id(binding["org_id"]).username
                        child_subscription["metadata"] = metadata
                        child_subscriptions.append(child_subscription)

                        number_of_bindings += binding["quantity"]

                    remaining_unbound = subscription["quantity"] - number_of_bindings
                    if remaining_unbound > 0:
                        subscription["quantity"] = remaining_unbound
                        subscription["assigned_to_org"] = None
                    else:
                        # all quantities for this subscription are bound, remove it from
                        # the response body
                        user_subscriptions.remove(subscription)

                else:
                    # default case, only one org is bound
                    subscription["assigned_to_org"] = model.organization.get_organization_by_id(
                        bindings[0]["org_id"]
                    ).username
            else:
                subscription["assigned_to_org"] = None

            subscription["metadata"] = metadata

        return user_subscriptions + child_subscriptions
