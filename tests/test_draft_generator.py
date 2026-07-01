from draft_generator import DraftGenerator, clean_draft, fallback_draft


class Client:
    class Chat:
        class Completions:
            def create(self, **kwargs):
                return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "Bonjour, merci pour votre message."})()})()]})()

        completions = Completions()

    chat = Chat()


def test_draft_generation():
    assert DraftGenerator("", client=Client()).generate("Bonjour", "a@b.com", "Bonjour").startswith("Bonjour")


def test_draft_generation_accepts_signature_name():
    draft = DraftGenerator("", client=Client()).generate("Bonjour", "a@b.com", "Bonjour", signature_name="Jean Martin")
    assert draft.startswith("Bonjour")


def test_clean_draft_removes_reasoning_tags():
    raw = """<penser>
Je dois répondre en français et rester prudent.
</penser>

Bonjour,
Merci pour votre message. Je reste disponible pour échanger par courriel.

Cordialement,"""
    cleaned = clean_draft(raw)
    assert "<penser>" not in cleaned
    assert "Je dois répondre" not in cleaned
    assert cleaned.startswith("Bonjour,")


def test_clean_draft_keeps_first_real_greeting_after_preface():
    raw = """Voici une proposition :

Bonjour,
Merci pour votre message."""
    assert clean_draft(raw) == "Bonjour,\nMerci pour votre message."


def test_clean_draft_removes_placeholder_signature():
    assert "[Votre nom]" not in clean_draft("Bonjour,\nMerci.\n[Votre nom]")


class FailingClient:
    class Chat:
        class Completions:
            def create(self, **kwargs):
                raise RuntimeError("rate limit")

        completions = Completions()

    chat = Chat()


def test_safe_draft_generation_uses_fallback_with_signature():
    draft = DraftGenerator("", client=FailingClient()).safe_generate(
        "Facture juin",
        "a@b.com",
        "Bonjour, veuillez trouver la facture.",
        signature_name="Jean Martin",
    )
    assert "Bonjour" in draft
    assert "Jean Martin" in draft


def test_fallback_draft_uses_english_when_email_is_english():
    draft = fallback_draft("Invoice", "Hello, please review this invoice.", "Jean Martin")
    assert draft.startswith("Hello")
    assert "Best regards" in draft
