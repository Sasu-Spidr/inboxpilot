from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_registration_requires_explicit_ai_consent():
    route = (ROOT / "frontend/app/api/auth/register/route.ts").read_text(encoding="utf-8")
    assert 'form.get("aiProcessingConsent") === "on"' in route
    assert "aiConsentVersion !== AI_CONSENT_VERSION" in route


def test_worker_fails_closed_without_consent():
    worker = (ROOT / "main.py").read_text(encoding="utf-8")
    consent = (ROOT / "consent_state.py").read_text(encoding="utf-8")
    assert "ai_processing_consent_granted(client_id)" in worker
    assert "return False" in consent


def test_account_rights_routes_and_documentation_exist():
    expected = [
        "frontend/app/api/account/export-data/route.ts",
        "frontend/app/api/account/delete-account/route.ts",
        "frontend/app/account/export-data/page.tsx",
        "frontend/app/account/delete-account/page.tsx",
        "docs/RGPD_COMPLIANCE.md",
    ]
    assert all((ROOT / filename).is_file() for filename in expected)


def test_export_excludes_credentials_and_is_scoped_to_client():
    source = (ROOT / "frontend/lib/accountPrivacy.ts").read_text(encoding="utf-8")
    assert "readActivityEvents(user.client_id)" in source
    assert "event.client_id === user.client_id" in source
    assert "password_hash" not in source
    assert "mfa_secret" not in source
    assert "token_file" not in source
