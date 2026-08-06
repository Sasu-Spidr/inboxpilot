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


class KeepUnreadClassifier:
    def safe_classify(self, *args):
        return {"label": "À lire", "action": "mark_read", "priority": "low", "confidence": 0.9, "reason": "Information only"}


class CommercialClassifier:
    def safe_classify(self, *args):
        return {"label": "Commercial", "action": "keep", "priority": "low", "confidence": 0.95, "reason": "Commercial email"}


class State:
    def __init__(self):
        self.records = set()
        self.completed = []

    def is_processed(self, *args):
        return args in self.records

    def get(self, *args):
        return {}

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
    assert "À lire" in call[1][2]
    assert "Commercial" in call[1][2]


def test_worker_classifies_personal_job_alerts_as_commercial(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])

    class JobConnector(Connector):
        def unread_emails(self, limit):
            return [
                {
                    "id": "job-1",
                    "subject": "Indeed - QUALIBAT recherche un/e Développeur Data & IA + 9 nouvelles offres",
                    "sender": "Indeed <alert@indeed.com>",
                    "body": "Offres de stage et alternance à Paris.",
                    "thread_id": "t",
                }
            ]

    class WrongClassifier:
        def safe_classify(self, *args, **kwargs):
            return {"label": "À lire", "action": "keep", "priority": "low", "confidence": 0.95, "reason": "Wrong default"}

    c = JobConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(
        settings,
        connectors={"ilyesseeladaoui2-gmail-com": {"gmail:gmail-2": {"name": "gmail", "account": "gmail-2", "connector": c}}},
        classifier=WrongClassifier(),
        drafts=Drafts(),
        state=State(),
    )
    worker.run_cycle()
    assert c.calls[0][0] == "replace_label"
    assert c.calls[0][1][1] == "Commercial"


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


def test_worker_keeps_message_unread_by_default(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    c = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=KeepUnreadClassifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert "read" not in [x[0] for x in c.calls]


def test_worker_never_marks_message_as_read_even_when_label_setting_allows_it(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"Commercial","name":"Commercial","color":"#fb7185","prepareDraft":false,"autoReply":false,"autoDelete":false,"markAsRead":true}]}',
        encoding="utf-8",
    )
    c = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=CommercialClassifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert "read" not in [x[0] for x in c.calls]


def test_worker_keeps_unread_message_when_delay_is_set_without_auto_delete(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"Commercial","name":"Commercial","color":"#fb7185","prepareDraft":false,"autoReply":false,"autoDelete":false,"autoDeleteUnreadAfterDays":1}]}',
        encoding="utf-8",
    )

    class OldUnreadConnector(Connector):
        def unread_emails(self, limit):
            return [{"id": "1", "subject": "Promo", "sender": "shop@example.com", "body": "Hello", "thread_id": "t", "received_at": "2026-01-01T00:00:00Z"}]

    c = OldUnreadConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    class DelayedClassifier:
        def safe_classify(self, *args):
            return {"label": "Commercial", "action": "keep", "priority": "high", "confidence": 0.95, "reason": "Commercial"}

    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=DelayedClassifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert "trash" not in [x[0] for x in c.calls]


def test_worker_guards_commercial_auto_delete_without_mass_signal(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"Commercial","name":"Commercial","color":"#fb7185","prepareDraft":false,"autoReply":false,"autoDelete":true}]}',
        encoding="utf-8",
    )

    class MarketingClassifier:
        def safe_classify(self, *args):
            return {"label": "Commercial", "action": "keep", "priority": "low", "confidence": 0.95, "reason": "Marketing email"}

    c = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=MarketingClassifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert "trash" not in [x[0] for x in c.calls]


def test_worker_deletes_old_unread_commercial_after_delay(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"Commercial","name":"Commercial","color":"#fb7185","prepareDraft":false,"autoReply":false,"autoDelete":true,"autoDeleteUnreadAfterDays":1}]}',
        encoding="utf-8",
    )

    class OldUnreadConnector(Connector):
        def unread_emails(self, limit):
            return [{"id": "1", "subject": "Promo", "sender": "shop@example.com", "body": "Hello", "thread_id": "t", "received_at": "2026-01-01T00:00:00Z"}]

    class MarketingClassifier:
        def safe_classify(self, *args):
            return {"label": "Commercial", "action": "keep", "priority": "low", "confidence": 0.95, "reason": "Marketing email"}

    c = OldUnreadConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=MarketingClassifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert "trash" in [x[0] for x in c.calls]


def test_worker_deletes_already_processed_unread_message_after_delay(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"Commercial","name":"Commercial","color":"#fb7185","prepareDraft":false,"autoReply":false,"autoDelete":true,"autoDeleteUnreadAfterDays":1}]}',
        encoding="utf-8",
    )

    class OldUnreadConnector(Connector):
        def unread_emails(self, limit):
            return [{"id": "1", "subject": "Promo", "sender": "shop@example.com", "body": "Hello", "thread_id": "t", "received_at": "2026-01-01T00:00:00Z"}]

    class CompletedState(State):
        def is_processed(self, *args):
            return True

        def get(self, *args):
            return {"label": "Commercial", "thread_id": "t", "draft_created": False}

    c = OldUnreadConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=CommercialClassifier(), drafts=Drafts(), state=CompletedState())
    worker.run_cycle()
    assert c.calls == [("trash", ("1",))]


def test_worker_reconciles_processed_unread_label_without_marking_read(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])

    class CompletedState(State):
        def is_processed(self, *args):
            return True

        def get(self, *args):
            return {"label": "À lire", "thread_id": "t", "draft_created": False, "action": "keep"}

    c = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=CommercialClassifier(), drafts=Drafts(), state=CompletedState())
    worker.run_cycle()
    replace_call = c.calls[0]
    assert replace_call[0] == "replace_label"
    assert replace_call[1][1] == "À lire"
    assert {"À répondre", "À traiter", "À lire", "Notification", "Commercial", "FYI", "Marketing"}.issubset(set(replace_call[1][2]))
    assert "read" not in [x[0] for x in c.calls]
    assert "draft" not in [x[0] for x in c.calls]


def test_worker_cleans_legacy_labels_on_already_processed_message_once(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])

    class CompletedState(State):
        def __init__(self):
            super().__init__()
            self.record = {"label": "Notification", "thread_id": "t", "draft_created": False, "action": "keep"}

        def is_processed(self, *args):
            return True

        def get(self, *args):
            return self.record

        def complete(self, **kwargs):
            self.record = kwargs
            self.completed.append(kwargs)

    c = Connector()
    state = CompletedState()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"hotmail:main": {"name": "hotmail", "account": "main", "connector": c}}}, classifier=CommercialClassifier(), drafts=Drafts(), state=state)

    worker.run_cycle()
    worker.run_cycle()

    replace_calls = [call for call in c.calls if call[0] == "replace_label"]
    assert len(replace_calls) == 1
    assert replace_calls[0][1][1] == "Notification"
    assert {"À répondre", "À traiter", "À lire", "Notification", "Commercial", "FYI", "Marketing"}.issubset(set(replace_calls[0][1][2]))
    assert state.record["legacy_labels_cleaned_at"]
    assert state.record["legacy_labels_cleanup_version"] == 3
    assert "read" not in [x[0] for x in c.calls]
    assert "trash" not in [x[0] for x in c.calls]


def test_worker_recleans_legacy_labels_when_previous_cleanup_has_no_version(monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])

    class CompletedState(State):
        def __init__(self):
            super().__init__()
            self.record = {"label": "À lire", "thread_id": "t", "draft_created": False, "action": "keep", "legacy_labels_cleaned_at": "old"}

        def is_processed(self, *args):
            return True

        def get(self, *args):
            return self.record

        def complete(self, **kwargs):
            self.record = kwargs
            self.completed.append(kwargs)

    c = Connector()
    state = CompletedState()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=CommercialClassifier(), drafts=Drafts(), state=state)

    worker.run_cycle()

    replace_calls = [call for call in c.calls if call[0] == "replace_label"]
    assert len(replace_calls) == 1
    assert replace_calls[0][1][1] == "À lire"
    assert "FYI" in replace_calls[0][1][2]
    assert state.record["legacy_labels_cleanup_version"] == 3


def test_worker_guards_auto_delete_without_mass_signal(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"Commercial","name":"Commercial","color":"#fb7185","prepareDraft":false,"autoReply":false,"autoDelete":true}]}',
        encoding="utf-8",
    )
    c = Connector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=CommercialClassifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert "trash" not in [x[0] for x in c.calls]


def test_worker_syncs_gmail_label_color_from_client_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"À répondre","name":"À répondre","color":"#4338ca","prepareDraft":true,"autoReply":false,"autoDelete":false}]}',
        encoding="utf-8",
    )

    class ColorConnector(Connector):
        def sync_label_color(self, *args):
            self.calls.append(("color", args))

    c = ColorConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=Classifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert ("color", ("À répondre", "#4338ca")) in c.calls


def test_worker_syncs_gmail_label_color_even_without_new_email(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"À traiter","name":"À traiter","color":"#856082","prepareDraft":false,"autoReply":false,"autoDelete":false}]}',
        encoding="utf-8",
    )

    class EmptyColorConnector(Connector):
        def unread_emails(self, limit):
            return []

        def sync_label_color(self, *args):
            self.calls.append(("color", args))

    c = EmptyColorConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"gmail:main": {"name": "gmail", "account": "main", "connector": c}}}, classifier=Classifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert ("color", ("À traiter", "#856082")) in c.calls
    assert ("color", ("Commercial", "#fb7185")) in c.calls


def test_worker_syncs_hotmail_label_color_even_without_new_email(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "exuvie.json").write_text(
        '{"labels":[{"key":"À traiter","name":"À traiter","color":"#0a6cff","prepareDraft":false,"autoReply":false,"autoDelete":false}]}',
        encoding="utf-8",
    )

    class EmptyColorConnector(Connector):
        def unread_emails(self, limit):
            return []

        def sync_label_color(self, *args):
            self.calls.append(("color", args))

    c = EmptyColorConnector()
    settings = {"groq_api_key": "x", "max_emails_per_cycle": 1, "token_encryption_key": "x"}
    worker = MailWorker(settings, connectors={"exuvie": {"hotmail:main": {"name": "hotmail", "account": "main", "connector": c}}}, classifier=Classifier(), drafts=Drafts(), state=State())
    worker.run_cycle()
    assert ("color", ("À traiter", "#0a6cff")) in c.calls
    assert ("color", ("Commercial", "#fb7185")) in c.calls


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
