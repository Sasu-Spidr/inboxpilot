from __future__ import annotations
import logging
import re
from urllib.parse import quote
import msal
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from token_store import TokenStore

LOG = logging.getLogger(__name__)
SCOPES = ["Mail.ReadWrite", "Mail.Read", "User.Read", "MailboxSettings.ReadWrite"]
GRAPH = "https://graph.microsoft.com/v1.0"


OUTLOOK_CATEGORY_COLORS = {
    "preset0": "#c4314b",  # Red
    "preset1": "#e67c20",  # Orange
    "preset2": "#8e562e",  # Brown
    "preset3": "#f2c744",  # Yellow
    "preset4": "#2c9f45",  # Green
    "preset5": "#00a3a3",  # Teal
    "preset6": "#6b8e23",  # Olive
    "preset7": "#3175d1",  # Blue
    "preset8": "#7b61c9",  # Purple
    "preset9": "#c23977",  # Cranberry
    "preset10": "#8796a5",  # Steel
    "preset11": "#4b5f73",  # DarkSteel
    "preset12": "#8a8a8a",  # Gray
    "preset13": "#5f5f5f",  # DarkGray
    "preset14": "#1f2937",  # Black
}


class HotmailConnector:
    def __init__(self, client_id: str, tenant_id: str, token_file: str, token_store: TokenStore, session=None, client_secret: str = ""):
        if not client_id: raise ValueError("MICROSOFT_CLIENT_ID is required when Hotmail is enabled")
        self.client_id, self.authority, self.token_file, self.store = client_id, f"https://login.microsoftonline.com/{tenant_id}", token_file, token_store
        self.client_secret = client_secret
        self.session = session or requests.Session(); self.access_token = None

    def authenticate(self) -> None:
        if self.access_token: return
        cache = msal.SerializableTokenCache(); saved = self.store.load(self.token_file)
        if saved: cache.deserialize(saved["cache"])
        if self.client_secret:
            app = msal.ConfidentialClientApplication(self.client_id, client_credential=self.client_secret, authority=self.authority, token_cache=cache)
        else:
            app = msal.PublicClientApplication(self.client_id, authority=self.authority, token_cache=cache)
        accounts = app.get_accounts(); result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
        if not result:
            if self.client_secret:
                raise RuntimeError("Microsoft token cache is empty; reconnect Hotmail from the web dashboard")
            flow = app.initiate_device_flow(scopes=SCOPES)
            if "message" not in flow: raise RuntimeError(f"Unable to start Microsoft device flow: {flow}")
            print(flow["message"], flush=True)
            result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result: raise RuntimeError(f"Microsoft authentication failed: {result.get('error_description', result)}")
        self.access_token = result["access_token"]; self.store.save(self.token_file, {"cache": cache.serialize()})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True,
           retry=retry_if_exception_type(requests.RequestException))
    def _request(self, method: str, path: str, **kwargs):
        self.authenticate(); response = self.session.request(method, GRAPH + path, headers={"Authorization": f"Bearer {self.access_token}"}, timeout=30, **kwargs)
        response.raise_for_status(); return response.json() if response.content else {}

    def unread_emails(self, limit: int) -> list[dict]:
        data = self._request("GET", "/me/mailFolders/inbox/messages", params={"$filter": "isRead eq false", "$top": limit, "$select": "id,subject,from,body,conversationId,receivedDateTime"})
        return [self._email_from_graph(x) for x in data.get("value", [])]

    def get_email(self, message_id: str) -> dict:
        data = self._request("GET", f"/me/messages/{message_id}", params={"$select": "id,subject,from,body,conversationId,receivedDateTime"})
        return self._email_from_graph(data)

    def _email_from_graph(self, item: dict) -> dict:
        return {"id": item["id"], "subject": item.get("subject", ""), "sender": item.get("from", {}).get("emailAddress", {}).get("address", ""), "body": item.get("body", {}).get("content", ""), "thread_id": item.get("conversationId"), "received_at": item.get("receivedDateTime")}

    def apply_label(self, message_id: str, category: str) -> None:
        self._request("PATCH", f"/me/messages/{message_id}", json={"categories": [category]})

    def sync_label_color(self, category_name: str, preferred_color: str) -> None:
        category_id = self._category_id(category_name)
        color = outlook_category_color(preferred_color)
        self._request("PATCH", f"/me/outlook/masterCategories/{quote(category_id, safe='')}", json={"color": color})

    def replace_label(self, message_id: str, category: str, managed_categories: list[str]) -> None:
        data = self._request("GET", f"/me/messages/{message_id}", params={"$select": "categories"})
        existing = data.get("categories", []) or []
        categories = [item for item in existing if item not in set(managed_categories)]
        if category not in categories:
            categories.append(category)
        self._request("PATCH", f"/me/messages/{message_id}", json={"categories": categories})

    def trash(self, message_id: str) -> None: self._request("POST", f"/me/messages/{message_id}/move", json={"destinationId": "deleteditems"})
    def archive(self, message_id: str) -> None: self._request("POST", f"/me/messages/{message_id}/move", json={"destinationId": "archive"})
    def move(self, message_id: str, target: str) -> None: self._request("POST", f"/me/messages/{message_id}/move", json={"destinationId": target})
    def mark_read(self, message_id: str) -> None: self._request("PATCH", f"/me/messages/{message_id}", json={"isRead": True})
    def create_draft(self, email: dict, text: str) -> None:
        self._request("POST", f"/me/messages/{email['id']}/createReply", json={"comment": text})

    def _category_id(self, display_name: str) -> str:
        data = self._request("GET", "/me/outlook/masterCategories")
        for category in data.get("value", []) or []:
            if category.get("displayName") == display_name:
                return category["id"]
        created = self._request(
            "POST",
            "/me/outlook/masterCategories",
            json={"displayName": display_name, "color": "preset12"},
        )
        return created["id"]


def outlook_category_color(preferred_color: str) -> str:
    preferred = hex_to_rgb(preferred_color)
    return min(OUTLOOK_CATEGORY_COLORS, key=lambda preset: color_distance(preferred, hex_to_rgb(OUTLOOK_CATEGORY_COLORS[preset])))


def color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum((a - b) ** 2 for a, b in zip(left, right))


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    value = color.strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{6}", value):
        return (138, 138, 138)
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))
