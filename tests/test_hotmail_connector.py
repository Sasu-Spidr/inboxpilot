from hotmail_connector import HotmailConnector, outlook_category_color
from token_store import TokenStore


class Resp:
    content = b"x"

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "value": [
                {
                    "id": "1",
                    "subject": "Test",
                    "from": {"emailAddress": {"address": "x@y.com"}},
                    "body": {"content": "hello"},
                    "conversationId": "c",
                }
            ]
        }


class Session:
    def request(self, *args, **kwargs):
        return Resp()


def test_reads_unread_email():
    c = HotmailConnector("id", "consumers", "unused", TokenStore(TokenStore.generate_key()), session=Session())
    c.access_token = "token"
    assert c.unread_emails(1)[0]["sender"] == "x@y.com"


def test_outlook_category_color_maps_to_closest_preset():
    assert outlook_category_color("#14b8a6") == "preset5"
    assert outlook_category_color("#0a6cff") == "preset7"
    assert outlook_category_color("#dc4c4c") == "preset0"


def test_sync_label_color_creates_missing_managed_category():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET":
                return {"value": []}
            if method == "POST":
                return {"id": "cat-id"}
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )
    connector.sync_label_color("À traiter", "#0a6cff")

    assert calls == [
        ("GET", "/me/outlook/masterCategories", {}),
        ("POST", "/me/outlook/masterCategories", {"json": {"displayName": "À traiter", "color": "preset7"}}),
        ("PATCH", "/me/outlook/masterCategories/cat-id", {"json": {"color": "preset7"}}),
    ]


def test_delete_label_removes_existing_outlook_category():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET":
                return {"value": [{"id": "old/category id", "displayName": "Commercial"}]}
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )

    assert connector.delete_label(" commercial ") is True
    assert calls == [
        ("GET", "/me/outlook/masterCategories", {}),
        ("DELETE", "/me/outlook/masterCategories/old%2Fcategory%20id", {}),
    ]


def test_replace_label_creates_missing_managed_category():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET" and path == "/me/messages/message-id":
                return {"categories": ["À lire", "Client"]}
            if method == "GET" and path == "/me/outlook/masterCategories":
                return {"value": []}
            if method == "POST":
                return {"id": "category-id"}
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )
    connector.replace_label("message-id", "Notification", ["Notification", "À lire"])

    assert calls == [
        ("GET", "/me/outlook/masterCategories", {}),
        ("POST", "/me/outlook/masterCategories", {"json": {"displayName": "Notification", "color": "preset12"}}),
        ("GET", "/me/messages/message-id", {"params": {"$select": "categories"}}),
        ("PATCH", "/me/messages/message-id", {"json": {"categories": ["Client", "Notification"]}}),
    ]


def test_replace_label_creates_configured_custom_outlook_category():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET" and path == "/me/messages/message-id":
                return {"categories": ["Client"]}
            if method == "GET" and path == "/me/outlook/masterCategories":
                return {"value": []}
            if method == "POST":
                return {"id": "custom-id"}
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )
    connector.replace_label("message-id", "Custom", ["Custom"])

    assert calls == [
        ("GET", "/me/outlook/masterCategories", {}),
        ("POST", "/me/outlook/masterCategories", {"json": {"displayName": "Custom", "color": "preset12"}}),
        ("GET", "/me/messages/message-id", {"params": {"$select": "categories"}}),
        ("PATCH", "/me/messages/message-id", {"json": {"categories": ["Client", "Custom"]}}),
    ]


def test_replace_label_removes_existing_managed_and_legacy_categories():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET" and path == "/me/outlook/masterCategories":
                return {"value": [{"id": "cat-id", "displayName": "Commercial"}]}
            if method == "GET" and path == "/me/messages/message-id":
                return {"categories": ["À lire", "FYI", "Client perso"]}
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )
    connector.replace_label("message-id", "Commercial", ["À lire", "Commercial"])

    assert calls == [
        ("GET", "/me/outlook/masterCategories", {}),
        ("GET", "/me/messages/message-id", {"params": {"$select": "categories"}}),
        ("PATCH", "/me/messages/message-id", {"json": {"categories": ["Client perso", "Commercial"]}}),
    ]
