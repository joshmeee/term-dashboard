from termdash.sources.gmail_unread import GmailUnreadSource


class _FakeLabels:
    def get(self, userId, id):
        return _FakeRequest()


class _FakeUsers:
    def labels(self):
        return _FakeLabels()


class _FakeService:
    def users(self):
        return _FakeUsers()


class _FakeRequest:
    def execute(self):
        return {"messagesUnread": 7}


async def test_gmail_unread(monkeypatch):
    def fake_build(*args, **kwargs):
        return _FakeService()

    monkeypatch.setattr("termdash.sources.gmail_unread.build", fake_build)
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.refresh",
        lambda self, request: None,
    )

    source = GmailUnreadSource(
        "Gmail",
        120,
        {
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "token",
        },
    )
    data = await source.fetch()

    assert data.status == "ok"
    assert data.value == "7 unread"
