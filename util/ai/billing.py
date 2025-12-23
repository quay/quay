"""
Billing integration for AI features.

This module handles subscription checks for managed mode (quay.io),
where AI features require a paid subscription.
"""

import logging

from app import app

logger = logging.getLogger(__name__)


def is_managed_mode():
    """
    Check if the AI feature is running in managed mode (quay.io).

    In managed mode, Quay.io provides the LLM backend and users need a paid subscription.
    In BYOK (Bring Your Own Key) mode, users provide their own API keys.

    Returns:
        bool: True if running in managed mode, False for BYOK mode.
    """
    return app.config.get("AI_PROVIDER_MODE", "byok").lower() == "managed"


def org_has_ai_subscription(namespace_user):
    """
    Check if an organization/user has a valid subscription for AI features.

    This function checks both Stripe subscriptions and RH Marketplace subscriptions.

    Args:
        namespace_user: The User/Organization model instance.

    Returns:
        bool: True if the namespace has a valid paid subscription.
    """
    if namespace_user is None:
        return False

    # Check for Stripe subscription
    if namespace_user.stripe_id:
        try:
            from app import billing

            cus = billing.Customer.retrieve(namespace_user.stripe_id)
            if cus and cus.subscription:
                # Any active subscription grants AI access
                return True
        except Exception as e:
            logger.warning(f"Error checking Stripe subscription: {e}")
            # Fall through to RH Marketplace check

    # Check for RH Marketplace subscription
    try:
        import features

        if getattr(features, "RH_MARKETPLACE", False):
            from data.model import organization_skus

            if namespace_user.organization:
                # Check org-level RH subscriptions
                query = organization_skus.get_org_subscriptions(namespace_user.id)
                if query is not None and query.count() > 0:
                    return True
            else:
                # Check user-level RH subscriptions
                from app import marketplace_subscriptions, marketplace_users

                account_numbers = marketplace_users.get_account_number(namespace_user)
                if account_numbers:
                    for account_number in account_numbers:
                        subs = marketplace_subscriptions.get_list_of_subscriptions(
                            account_number, filter_out_org_bindings=True
                        )
                        if subs:
                            return True
    except Exception as e:
        logger.warning(f"Error checking RH Marketplace subscription: {e}")

    return False


def check_ai_subscription_required(namespace_user):
    """
    Check if AI subscription requirements are met.

    In BYOK mode, no subscription is required (users bring their own keys).
    In managed mode, a paid subscription is required.

    Args:
        namespace_user: The User/Organization model instance.

    Returns:
        tuple: (allowed: bool, error_message: str or None)
    """
    if not is_managed_mode():
        # BYOK mode - no subscription required
        return True, None

    if org_has_ai_subscription(namespace_user):
        return True, None

    return False, (
        "AI features require a paid subscription. "
        "Please upgrade your plan to access AI-powered description generation."
    )
