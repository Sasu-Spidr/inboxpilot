from pathlib import Path

from main import MailWorker, filter_settings


class Connector:
    def __init__(self, email_id="1"):
        self.calls = []
        self.email_id = email_id

    def unread_emails(self, limit):
        return [{"id": "1", "subject": "Need help", "sender": "a@b.com", "body": "Hello", "thread_id": "t"}]

    def get_email(self, message_id):
        return {"id": message_id, "subject": "Need help", "sender": "a@b.com", "body": "Hello", "thread_id": "t"}

    def apply_label(self, *args):
        self.calls.append(("label", args))

    def replace_label(self, *args):
        self.calls.append(("replace_label", args))

    def create_draft(self, *args):
        self.calls.append(("draft", args))

    def trash(self, *args):
        self.calls.append(("trash", args))

    def mark_read(self, *args):
        self.calls.append(("read", args))

    def archive(self, *args):
        self.calls.append(("archive", args))

    def move(self, *args):
        self.calls.append(("move", args))


class Classifier:
    def safe_classify(self, *args):
        return {"label": "À répondre", "action": "keep", "priority": "high", "confidence": 0.9, "reason": "Needs reply"}


class Drafts:
    def generate(self, *args, **kwargs):
        return "Hello"


class State:
    def __init__(self):
        self.records = set()
        self.completed = []

    def is_processed(self, *args):
        return args in self.records

    def begin(self, **kwargs):
        self.records.add((kwargs["client_id"], kwargs["connector"], kwargs["account"], kwargs["message_id"]))

    def complete(self, **kwargs):
        self.completed.append(kwargs)

    def remove(self, *args):
        self.records.discard(args)


def test_worker_creates_draft(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    c = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=Classifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert [x[0] for x in c.calls] == ["replace_label", "draft"]


def test_worker_replaces_managed_labels(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    c = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=Classifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    call = c.calls[0]
    assert call[0] == "replace_label"
    assert call[1][1] == "À répondre"
    assert "Commentaire" in call[1][2]
    assert "Marketing" in call[1][2]


def test_worker_passes_sender_name_to_draft(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])

    class CapturingDrafts(Drafts):
        def __init__(self):
            self.kwargs = None

        def generate(self, *args, **kwargs):
            self.kwargs = kwargs
            return "Hello"

    c = Connector()
    drafts = CapturingDrafts()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(
        settings,
        connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c, "sender_name": "Jean Martin"}}},
        classifier=Classifier(),
        drafts=drafts,
        state=State(),
    )
    worker.run_cycle()
    assert drafts.kwargs["signature_name"] == "Jean Martin"


def test_worker_does_not_process_duplicate(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    c = Connector()
    state = State()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=Classifier(), drafts=Drafts(), state=state)
    worker.run_cycle()
    worker.run_cycle()
    assert [x[0] for x in c.calls].count("draft") == 1


def test_error_on_one_email_does_not_block_next(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])

    class MultiConnector(Connector):
        def unread_emails(self, limit):
            return [
                {"id": "bad", "subject": "Need help", "sender": "a@b.com", "body": "Hello", "thread_id": "t"},
                {"id": "ok", "subject": "Need help", "sender": "a@b.com", "body": "Hello", "thread_id": "t"},
            ]

        def create_draft(self, email, text):
            if email["id"] == "bad":
                raise RuntimeError("draft failed")
            super().create_draft(email, text)

    c = MultiConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 2, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=Classifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert any(call[0] == "draft" and call[1][0]["id"] == "ok" for call in c.calls)


def test_multi_client_multi_mailbox(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    g = Connector()
    h = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    connectors = {
        "exuvie": {
            "gmail:main": {"name": "gmail", "account": "main", "connector": g},
            "hotmail:main": {"name": "hotmail", "account": "main", "connector": h},
        }
    }
    worker = MailWorker(settings, connectors=connectors, classifier=Classifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert [x[0] for x in g.calls] == ["replace_label", "draft"]
    assert [x[0] for x in h.calls] == ["replace_label", "draft"]


def test_filter_settings_targets_one_client_connector_account():
    settings = {
        "clients": {
            "exuvie": {"enabled": True, "connectors": {"gmail": {"enabled": True, "accounts": [{"account": "main"}]}}},
            "collegue": {"enabled": False, "connectors": {"gmail": {"enabled": True, "accounts": [{"account": "main"}]}, "hotmail": {"enabled": True, "accounts": [{"account": "main"}]}}},
        }
    }
    filtered = filter_settings(settings, client="collegue", connector="gmail", account="main")
    assert filtered["clients"]["exuvie"]["enabled"] is False
    assert filtered["clients"]["collegue"]["enabled"] is True
    assert filtered["clients"]["collegue"]["connectors"]["gmail"]["enabled"] is True
    assert filtered["clients"]["collegue"]["connectors"]["hotmail"]["enabled"] is False
