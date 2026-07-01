from __future__ import annotations
import base64
import logging
import re
from email.utils import parseaddr
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from token_store import TokenStore

LOG = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.compose"]


class GmailConnector:
    def __init__(self, credentials_file: str, token_file: str, token_store: TokenStore, service=None):
        self.credentials_file, self.token_file, self.store, self.service = credentials_file, token_file, token_store, service

    def authenticate(self) -> None:
        if self.service:
            return
        data = self.store.load(self.token_file)
        creds = Credentials.from_authorized_user_info(data, SCOPES) if data else None
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.store.save(self.token_file, json_credentials(creds))
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
            self.store.save(self.token_file, json_credentials(creds))
        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    def unread_emails(self, limit: int) -> list[dict]:
        self.authenticate()
        rows = self._execute(self.service.users().messages().list(userId="me", q="is:unread in:inbox", maxResults=limit)).get("messages", [])
        return [self.get_email(row["id"]) for row in rows]

    def get_email(self, message_id: str) -> dict:
        self.authenticate()
        msg = self._execute(self.service.users().messages().get(userId="me", id=message_id, format="full"))
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        return {"id": message_id, "subject": headers.get("subject", ""), "sender": headers.get("from", ""),
                "body": _gmail_body(msg["payload"]), "thread_id": msg.get("threadId")}

    def apply_label(self, message_id: str, label_name: str) -> None:
        self.authenticate(); label_id = self._label_id(label_name)
        self._execute(self.service.users().messages().modify(userId="me", id=message_id, body={"addLabelIds": [label_id]}))

    def replace_label(self, message_id: str, label_name: str, managed_labels: list[str]) -> None:
        self.authenticate()
        target_id = self._label_id(label_name)
        labels = self._execute(self.service.users().labels().list(userId="me")).get("labels", [])
        label_ids_by_name = {label["name"]: label["id"] for label in labels}
        remove_ids = [
            label_ids_by_name[name]
            for name in managed_labels
            if name != label_name and name in label_ids_by_name
        ]
        body = {"addLabelIds": [target_id]}
        if remove_ids:
            body["removeLabelIds"] = remove_ids
        self._execute(self.service.users().messages().modify(userId="me", id=message_id, body=body))

    def _label_id(self, name: str) -> str:
        labels = self._execute(self.service.users().labels().list(userId="me")).get("labels", [])
        for label in labels:
            if label["name"] == name: return label["id"]
        return self._execute(self.service.users().labels().create(userId="me", body={"name": name, "labelListVisibility": "labelShow"}))["id"]

    def trash(self, message_id: str) -> None:
        self.authenticate(); self._execute(self.service.users().messages().trash(userId="me", id=message_id))

    def archive(self, message_id: str) -> None:
        self.authenticate()
        self._execute(self.service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]}))

    def move(self, message_id: str, target: str) -> None:
        self.apply_label(message_id, target)
        self.archive(message_id)

    def mark_read(self, message_id: str) -> None:
        self.authenticate()
        self._execute(self.service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}))

    def create_draft(self, email: dict, text: str) -> None:
        self.authenticate()
        recipient = recipient_address(email.get("sender", ""))
        if not recipient:
            LOG.warning("Draft skipped because sender address is invalid: %s", email.get("sender", ""))
            return
        mime = MIMEText(text, "plain", "utf-8"); mime["To"] = recipient; mime["Subject"] = "Re: " + email["subject"]
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        self._execute(self.service.users().drafts().create(userId="me", body={"message": {"raw": raw, "threadId": email.get("thread_id")}}))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True,
           retry=retry_if_exception_type(Exception))
    def _execute(self, request):
        return request.execute()

def json_credentials(creds): return {"token": creds.token, "refresh_token": creds.refresh_token, "token_uri": creds.token_uri, "client_id": creds.client_id, "client_secret": creds.client_secret, "scopes": creds.scopes}
def recipient_address(sender: str) -> str:
    _, address = parseaddr(sender or "")
    if "@" in address and not re.search(r"\s", address):
        return address
    match = re.search(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+\.[A-Za-z]{2,}", sender or "")
    return match.group(0) if match else ""
def _gmail_body(payload):
    if payload.get("body", {}).get("data"): return base64.urlsafe_b64decode(payload["body"]["data"] + "===").decode("utf-8", "replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" or part.get("parts"):
            text = _gmail_body(part)
            if text: return text
    return ""
