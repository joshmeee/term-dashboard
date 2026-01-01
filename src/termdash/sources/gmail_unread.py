from __future__ import annotations

from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from termdash.sources.base import DataPoint, DataSource

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailUnreadSource(DataSource):
    async def fetch(self) -> DataPoint:
        client_id = self.options.get("client_id")
        client_secret = self.options.get("client_secret")
        refresh_token = self.options.get("refresh_token")

        if not client_id or not client_secret or not refresh_token:
            return DataPoint(
                title=self.name,
                value="Missing Gmail OAuth config",
                status="error",
                detail="Set client_id, client_secret, refresh_token.",
            )

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=[GMAIL_SCOPE],
        )
        creds.refresh(Request())

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        label = service.users().labels().get(userId="me", id="INBOX").execute()
        unread = label.get("messagesUnread", 0)

        return DataPoint(title=self.name, value=f"{unread} unread", status="ok")
