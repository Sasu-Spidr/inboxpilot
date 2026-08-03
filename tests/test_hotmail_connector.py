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


def test_sync_label_color_skips_missing_category():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET":
                return {"value": []}
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )
    connector.sync_label_color("À traiter", "#0a6cff")

    assert calls == [("GET", "/me/outlook/masterCategories", {})]


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


def test_replace_label_skips_missing_category():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET" and path == "/me/messages/message-id":
                return {"categories": ["Mise à jour de réunion", "Client"]}
            if method == "GET" and path == "/me/outlook/masterCategories":
                return {"value": []}
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )
    connector.replace_label("message-id", "Notification", ["Notification", "Mise à jour de réunion"])

    assert calls == [("GET", "/me/outlook/masterCategories", {})]


def test_replace_label_does_not_create_custom_outlook_category():
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
            return {}

    connector = CaptureHotmailConnector(
        "client-id",
        "consumers",
        "unused",
        TokenStore(TokenStore.generate_key()),
    )
    connector.replace_label("message-id", "Custom", ["Custom"])

    assert calls == [("GET", "/me/outlook/masterCategories", {})]
