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


def test_sync_label_color_creates_category_then_updates_color():
    calls = []

    class CaptureHotmailConnector(HotmailConnector):
        def authenticate(self):
            return None

        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET":
                return {"value": []}
            if method == "POST":
                return {"id": "category/id with spaces"}
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
        (
            "POST",
            "/me/outlook/masterCategories",
            {"json": {"displayName": "À traiter", "color": "preset12"}},
        ),
        (
            "PATCH",
            "/me/outlook/masterCategories/category%2Fid%20with%20spaces",
            {"json": {"color": "preset7"}},
        ),
    ]
