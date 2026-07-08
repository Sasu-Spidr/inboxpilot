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


def test_replace_label_creates_missing_label_and_removes_old_managed_labels():
    calls = []

    class LabelOps:
        def list(self, **kwargs):
            return Execute({"labels": [{"name": "Commentaire", "id": "old-comment"}]})

        def create(self, **kwargs):
            return CaptureExecute({"id": "new-label"}, calls, "create_label", kwargs)

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

    assert calls[0][0] == "create_label"
    assert calls[0][1]["body"]["name"] == "À traiter"
    assert calls[1][0] == "modify_message"
    assert calls[1][1]["body"] == {"addLabelIds": ["new-label"], "removeLabelIds": ["old-comment"]}


def test_sync_label_color_updates_existing_gmail_label():
    calls = []

    class LabelOps:
        def list(self, **kwargs):
            return Execute({"labels": [{"name": "À traiter", "id": "label-1"}]})

        def patch(self, **kwargs):
            return CaptureExecute({}, calls, "patch_label", kwargs)

    class CaptureUsers:
        def labels(self):
            return LabelOps()

    class CaptureService:
        def users(self):
            return CaptureUsers()

    c = GmailConnector("unused", "unused", TokenStore(TokenStore.generate_key()), service=CaptureService())
    c.sync_label_color("À traiter", "#8b5a83")

    assert calls == [
        (
            "patch_label",
            {
                "userId": "me",
                "id": "label-1",
                "body": {"color": gmail_label_color("#8b5a83")},
            },
        )
    ]


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
