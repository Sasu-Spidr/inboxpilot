from draft_generator import DraftGenerator, clean_draft


class Client:
    class Chat:
        class Completions:
            def create(self, **kwargs):
                return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "Bonjour, merci pour votre message."})()})()]})()

        completions = Completions()

    chat = Chat()


def test_draft_generation():
    assert DraftGenerator("", client=Client()).generate("Bonjour", "a@b.com", "Bonjour").startswith("Bonjour")


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
