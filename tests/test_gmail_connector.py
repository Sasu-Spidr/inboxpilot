import base64
from email import message_from_bytes

from gmail_connector import GmailConnector, gmail_label_color, recipient_address
from token_store import TokenStore

class Execute:
    def __init__(self, result): self.result=result
    def execute(self): return self.result


class CaptureExecute:
    def __init__(self, result, calls, name, kwargs):
        self.result = result
        self.calls = calls
        self.name = name
        self.kwargs = kwargs

    def execute(self):
        self.calls.append((self.name, self.kwargs))
        return self.result


class Messages:
    def list(self, **kwargs): return Execute({"messages":[{"id":"m1"}]})
    def get(self, **kwargs): return Execute({"threadId":"t1","payload":{"headers":[{"name":"Subject","value":"Hello"},{"name":"From","value":"x@y.com"}],"body":{"data":"SGk="}}})
class Users:
    def messages(self): return Messages()
class Service:
    def users(self): return Users()

def test_reads_unread_email():
    c=GmailConnector("unused","unused",TokenStore(TokenStore.generate_key()),service=Service())
    assert c.unread_emails(1) == [{"id":"m1","subject":"Hello","sender":"x@y.com","body":"Hi","thread_id":"t1"}]


def test_replace_label_skips_missing_label():
    calls = []

    class LabelOps:
        def list(self, **kwargs):
            return Execute({"labels": [{"name": "Commentaire", "id": "old-comment"}]})

    class MessageOps:
        def modify(self, **kwargs):
            return CaptureExecute({}, calls, "modify_message", kwargs)

    class CaptureUsers:
        def labels(self):
            return LabelOps()

        def messages(self):
            return MessageOps()

    class CaptureService:
        def users(self):
            return CaptureUsers()

    c = GmailConnector("unused", "unused", TokenStore(TokenStore.generate_key()), service=CaptureService())
    c.replace_label("msg-1", "À traiter", ["Commentaire", "Marketing", "À traiter"])

    assert calls == []


def test_sync_label_color_skips_missing_gmail_label():
    calls = []

    class LabelOps:
        def list(self, **kwargs):
            return Execute({"labels": []})

    class CaptureUsers:
        def labels(self):
            return LabelOps()

    class CaptureService:
        def users(self):
            return CaptureUsers()

    c = GmailConnector("unused", "unused", TokenStore(TokenStore.generate_key()), service=CaptureService())
    c.sync_label_color("À traiter", "#8b5a83")

    assert calls == []


def test_gmail_auth_without_token_does_not_open_browser(tmp_path, monkeypatch):
    monkeypatch.delenv("GMAIL_INTERACTIVE_AUTH", raising=False)
    c = GmailConnector(str(tmp_path / "missing-client.json"), str(tmp_path / "missing-token.enc"), TokenStore(TokenStore.generate_key()))
    try:
        c.authenticate()
    except RuntimeError as exc:
        assert "reconnect Gmail from the web dashboard" in str(exc)
    else:
        raise AssertionError("authenticate should fail without an OAuth token")


def test_create_draft_uses_plain_email_address_for_to_header():
    calls = []

    class DraftOps:
        def create(self, **kwargs):
            return CaptureExecute({}, calls, "create_draft", kwargs)

    class CaptureUsers:
        def drafts(self):
            return DraftOps()

    class CaptureService:
        def users(self):
            return CaptureUsers()

    c = GmailConnector("unused", "unused", TokenStore(TokenStore.generate_key()), service=CaptureService())
    c.create_draft(
        {"sender": "Jean Martin <jean@example.com>", "subject": "Bonjour", "thread_id": "t1"},
        "Bonjour",
    )

    raw = calls[0][1]["body"]["message"]["raw"]
    message = message_from_bytes(base64.urlsafe_b64decode(raw.encode()))
    assert message["To"] == "jean@example.com"


def test_recipient_address_extracts_embedded_email():
    assert recipient_address("Jean Martin <jean@example.com>") == "jean@example.com"
    assert recipient_address("Jean Martin jean@example.com") == "jean@example.com"
