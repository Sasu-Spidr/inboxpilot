from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_stripe_routes_and_dependency_are_packaged():
    package = read("frontend/package.json")
    assert '"stripe"' in package
    for path in (
        "frontend/app/api/checkout/route.ts",
        "frontend/app/api/billing/portal/route.ts",
        "frontend/app/api/webhooks/stripe/route.ts",
    ):
        assert (ROOT / path).is_file()


def test_checkout_and_portal_require_an_inboxpilot_session():
    checkout = read("frontend/app/api/checkout/route.ts")
    portal = read("frontend/app/api/billing/portal/route.ts")
    for route in (checkout, portal):
        assert "await currentUser()" in route
        assert "if (!user)" in route
    assert 'mode: "subscription"' in checkout
    assert "billingPortal.sessions.create" in portal


def test_webhook_verifies_signature_and_handles_required_events():
    webhook = read("frontend/app/api/webhooks/stripe/route.ts")
    assert 'request.headers.get("stripe-signature")' in webhook
    assert "request.text()" in webhook
    assert "webhooks.constructEvent" in webhook
    for event in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
    ):
        assert event in webhook


def test_subscription_state_is_persisted_and_cancel_returns_to_free():
    database = read("frontend/lib/db.ts")
    webhook = read("frontend/app/api/webhooks/stripe/route.ts")
    for column in (
        "subscription_tier",
        "subscription_status",
        "stripe_customer_id",
        "stripe_subscription_id",
    ):
        assert f"add column if not exists {column}" in database
    assert 'tier: "free"' in webhook
    assert 'status: "canceled"' in webhook
    assert '"past_due"' in webhook


def test_stripe_secrets_are_read_from_openbao_and_not_the_environment():
    resolver = read("frontend/lib/baoSecrets.ts")
    stripe = read("frontend/lib/stripe.ts")
    compose = yaml.safe_load(read("docker-compose.yml"))
    frontend_environment = compose["services"]["frontend"]["environment"]

    assert 'field: "stripe_secret_key"' in resolver
    assert 'field: "stripe_webhook_secret"' in resolver
    assert 'secret("STRIPE_SECRET_KEY")' in stripe
    assert 'secret("STRIPE_WEBHOOK_SECRET")' in stripe
    assert "STRIPE_SECRET_KEY" not in frontend_environment
    assert "STRIPE_WEBHOOK_SECRET" not in frontend_environment


def test_price_ids_are_non_secret_runtime_variables():
    compose = yaml.safe_load(read("docker-compose.yml"))
    frontend_environment = compose["services"]["frontend"]["environment"]
    workflow = read(".github/workflows/deploy.yml")
    for name in (
        "STRIPE_PRICE_PRO_MONTHLY",
        "STRIPE_PRICE_PRO_YEARLY",
        "STRIPE_PRICE_BUSINESS_MONTHLY",
        "STRIPE_PRICE_BUSINESS_YEARLY",
    ):
        assert name in frontend_environment
        assert f"{name}: ${{{{ vars.{name} }}}}" in workflow
