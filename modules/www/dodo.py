"""Dodo Payments integration helpers.

Reads configuration from the environment at call time (the app's config
classes evaluate before .env is loaded, so env vars must be exported):

    DODO_PAYMENTS_API_KEY      API key from Developer -> API Keys
    DODO_PAYMENTS_WEBHOOK_KEY  signing secret from Developer -> Webhooks
    DODO_PAYMENTS_ENVIRONMENT  test_mode (default) or live_mode
    DODO_PRODUCT_ID_PRO        product id of the Pro subscription

Checkout sessions are created server-side and the customer is redirected
to the hosted checkout. Fulfillment happens exclusively from the signed
webhook — never from the browser redirect.
"""

import os

from flask import url_for
from sqlalchemy import func

PRO_PLAN = 1
ENTERPRISE_PLAN = 2


def environment():
    return os.environ.get("DODO_PAYMENTS_ENVIRONMENT", "test_mode")


def get_client():
    """Return a DodoPayments client, or None when payments aren't configured."""
    api_key = os.environ.get("DODO_PAYMENTS_API_KEY")
    if not api_key:
        return None
    try:
        from dodopayments import DodoPayments
    except ImportError:
        return None
    return DodoPayments(
        bearer_token=api_key,
        webhook_key=os.environ.get("DODO_PAYMENTS_WEBHOOK_KEY"),
        environment=environment(),
    )


def is_configured():
    return bool(
        os.environ.get("DODO_PAYMENTS_API_KEY")
        and os.environ.get("DODO_PRODUCT_ID_PRO")
    )


def product_id_for_plan(plan):
    """Map a plan number to its Dodo product id (env-configured)."""
    if plan == ENTERPRISE_PLAN:
        return os.environ.get("DODO_PRODUCT_ID_ENTERPRISE")
    return os.environ.get("DODO_PRODUCT_ID_PRO")


def create_checkout(user, plan=PRO_PLAN):
    """Create a hosted checkout session for the given plan.

    Returns the checkout_url, or raises RuntimeError with a friendly message.
    """
    client = get_client()
    if client is None:
        raise RuntimeError("Payments are not configured (DODO_PAYMENTS_API_KEY)")
    product_id = product_id_for_plan(plan)
    if not product_id:
        raise RuntimeError(
            "Payments are not configured "
            "(DODO_PRODUCT_ID_ENTERPRISE)" if plan == ENTERPRISE_PLAN
            else "Payments are not configured (DODO_PRODUCT_ID_PRO)"
        )

    session = client.checkout_sessions.create(
        product_cart=[{"product_id": product_id, "quantity": 1}],
        customer={"email": user.email},
        return_url=url_for("www.dodo_return", plan=plan, _external=True),
    )
    return session.checkout_url


def verify_webhook(raw_body, headers):
    """Verify the webhook signature and parse the event.

    raw_body must be the exact bytes received, before any JSON parsing.
    Returns the parsed event dict; raises on invalid signature.
    """
    client = get_client()
    if client is None:
        raise RuntimeError("Payments are not configured (DODO_PAYMENTS_WEBHOOK_KEY)")
    return client.webhooks.unwrap(
        raw_body,
        headers={
            "webhook-id": headers.get("webhook-id", ""),
            "webhook-signature": headers.get("webhook-signature", ""),
            "webhook-timestamp": headers.get("webhook-timestamp", ""),
        },
    )


def _extract_email(data):
    """Best-effort customer email extraction across Dodo payload variants."""
    if not isinstance(data, dict):
        return None
    for key in ("customer_email", "email"):
        if data.get(key):
            return data[key]
    customer = data.get("customer")
    if isinstance(customer, dict) and customer.get("email"):
        return customer["email"]
    billing = data.get("billing_address")
    if isinstance(billing, dict) and billing.get("email"):
        return billing["email"]
    return None


def _extract_product_id(data):
    """Best-effort product id extraction across Dodo payload variants."""
    if not isinstance(data, dict):
        return None
    if data.get("product_id"):
        return data["product_id"]
    for key in ("products", "product_cart"):
        items = data.get(key)
        if isinstance(items, list) and items and isinstance(items[0], dict):
            if items[0].get("product_id"):
                return items[0]["product_id"]
    subscription = data.get("subscription")
    if isinstance(subscription, dict) and subscription.get("product_id"):
        return subscription["product_id"]
    return None


def plan_for_product(product_id):
    """Map a Dodo product id to our plan number, or None if unknown."""
    if not product_id:
        return None
    if product_id == os.environ.get("DODO_PRODUCT_ID_PRO"):
        return PRO_PLAN
    if product_id == os.environ.get("DODO_PRODUCT_ID_ENTERPRISE"):
        return ENTERPRISE_PLAN
    return None


def fulfill_event(event):
    """Apply a verified webhook event to the matching user.

    Returns a human-readable description of what happened (for logging),
    or None when the event needs no user-level action.

    Upgrades are idempotent (never lower an existing plan), so retried
    webhooks are harmless. Payment failures / cancellations downgrade the
    user to Free, which turns off every plan-gated feature automatically.
    """
    from modules.box__default.auth.models import User

    # the SDK returns typed pydantic events; unwrap to plain dicts
    if hasattr(event, "model_dump"):
        event = event.model_dump()
    elif hasattr(event, "dict"):
        event = event.dict()

    event_type = event.get("type", "")
    data = event.get("data") or {}

    if event_type in ("payment.succeeded", "subscription.active",
                      "subscription.trialing"):
        email = _extract_email(data)
        if not email:
            return f"{event_type}: no customer email in payload"
        product_id = _extract_product_id(data)
        plan = plan_for_product(product_id)
        if plan is None and product_id is not None:
            # a different product sold on the same Dodo account: not ours
            return f"{event_type}: unknown product {product_id}, ignored"
        plan = plan or PRO_PLAN  # legacy payloads without a product id
        user = User.query.filter(func.lower(User.email) == email.lower()).first()
        if not user:
            return f"{event_type}: no user for {email}"
        if (user.subscription_plan or 0) >= plan:
            return f"{event_type}: {user.username} already on plan {user.subscription_plan}"
        user.subscription_plan = plan
        user.save()
        return f"{event_type}: upgraded {user.username} to plan {plan}"

    if event_type in ("subscription.cancelled", "subscription.expired",
                      "subscription.on_hold"):
        email = _extract_email(data)
        if not email:
            return f"{event_type}: no customer email in payload"
        plan = plan_for_product(_extract_product_id(data))
        user = User.query.filter(func.lower(User.email) == email.lower()).first()
        if not user:
            return f"{event_type}: no user for {email}"
        current = user.subscription_plan or 0
        # downgrade when the cancelled product covers their current plan;
        # if the payload didn't identify the product, drop paid plans to free
        if current and (plan is None or current == plan):
            user.subscription_plan = 0
            user.save()
            return f"{event_type}: downgraded {user.username} to Free"
        return f"{event_type}: {user.username} on plan {current}, left untouched"

    return None
