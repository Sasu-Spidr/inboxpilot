from __future__ import annotations
import logging
import msal
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from token_store import TokenStore

LOG = logging.getLogger(__name__)
SCOPES = ["Mail.ReadWrite", "Mail.Read"]
GRAPH = "https://graph.microsoft.com/v1.0"


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
        data = self._request("GET", "/me/mailFolders/inbox/messages", params={"$filter": "isRead eq false", "$top": limit, "$select": "id,subject,from,body,conversationId"})
        return [self._email_from_graph(x) for x in data.get("value", [])]

    def get_email(self, message_id: str) -> dict:
        data = self._request("GET", f"/me/messages/{message_id}", params={"$select": "id,subject,from,body,conversationId"})
        return self._email_from_graph(data)

    def _email_from_graph(self, item: dict) -> dict:
        return {"id": item["id"], "subject": item.get("subject", ""), "sender": item.get("from", {}).get("emailAddress", {}).get("address", ""), "body": item.get("body", {}).get("content", ""), "thread_id": item.get("conversationId")}

    def apply_label(self, message_id: str, category: str) -> None:
        self._request("PATCH", f"/me/messages/{message_id}", json={"categories": [category]})

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
