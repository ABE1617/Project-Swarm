"""Google node tests against a mocked Google API (httpx.MockTransport).

Every test asserts what we SEND (URL, auth, payload encoding) and how we
parse what comes back - the parts that must be exactly right for the real API.
"""

import base64
import json

import httpx
import pytest

from app.engine.registry import get_registry
from app.engine.types import NodeContext, NodeExecutionError
from app.nodes import (
    _google,
    calendar_create_event,
    calendar_list_events,
    docs_create,
    drive_upload,
    gmail_read,
    gmail_send,
    sheets_append,
    sheets_read,
)


async def fake_credential(_credential_id):
    return {"type": "google_oauth2", "access_token": "test-token", "account_email": "t@g.com"}


def make_ctx(config: dict) -> NodeContext:
    config.setdefault("credential", 1)
    ctx = NodeContext(node_id="test", config=config)
    ctx.get_credential = fake_credential
    return ctx


@pytest.fixture
def transport(monkeypatch):
    """Install a MockTransport; tests set .handler and read .requests."""

    class Recorder:
        def __init__(self):
            self.requests: list[httpx.Request] = []
            self.handler = lambda request: httpx.Response(200, json={})

        def __call__(self, request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.handler(request)

    recorder = Recorder()
    monkeypatch.setattr(_google, "TRANSPORT", httpx.MockTransport(recorder))
    return recorder


# ---------- registry ----------


def test_google_nodes_registered():
    registry = get_registry()
    registry.load()
    for node_type in [
        "gmail_send",
        "gmail_read",
        "sheets_append",
        "sheets_read",
        "calendar_create_event",
        "calendar_list_events",
        "drive_upload",
        "docs_create",
    ]:
        spec = registry.get(node_type)
        assert spec is not None, node_type
        assert spec.category == "Google"
        assert spec.config_fields[0]["type"] == "credential"


# ---------- gmail ----------


async def test_gmail_send_builds_correct_mime(transport):
    transport.handler = lambda r: httpx.Response(200, json={"id": "m1", "threadId": "t1"})
    result = await gmail_send.run(
        make_ctx(
            {
                "to": "dest@example.com",
                "cc": "copy@example.com",
                "subject": "Hello world",
                "body_type": "text",
                "body": "line one\nline two",
            }
        )
    )
    request = transport.requests[0]
    assert request.url == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert request.headers["Authorization"] == "Bearer test-token"

    raw = json.loads(request.content)["raw"]
    mime = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
    assert "To: dest@example.com" in mime
    assert "Cc: copy@example.com" in mime
    assert "Subject: Hello world" in mime
    assert result == {
        "id": "m1",
        "thread_id": "t1",
        "to": "dest@example.com",
        "subject": "Hello world",
    }


async def test_gmail_read_lists_then_fetches(transport):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/messages"):
            assert request.url.params["q"] == "is:unread"
            assert request.url.params["maxResults"] == "5"
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        assert request.url.path.endswith("/messages/m1")
        body_data = base64.urlsafe_b64encode(b"the plain body").decode().rstrip("=")
        return httpx.Response(
            200,
            json={
                "id": "m1",
                "threadId": "t1",
                "snippet": "preview...",
                "labelIds": ["UNREAD"],
                "payload": {
                    "mimeType": "multipart/alternative",
                    "headers": [
                        {"name": "From", "value": "boss@example.com"},
                        {"name": "Subject", "value": "Quarterly"},
                    ],
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": body_data}},
                        {"mimeType": "text/html", "body": {"data": body_data}},
                    ],
                },
            },
        )

    transport.handler = handler
    result = await gmail_read.run(make_ctx({"query": "is:unread", "max_results": 5}))
    assert result["count"] == 1
    message = result["messages"][0]
    assert message["from"] == "boss@example.com"
    assert message["subject"] == "Quarterly"
    assert message["body"] == "the plain body"


# ---------- sheets ----------


def test_normalize_rows_variants():
    assert sheets_append.normalize_rows('["a", 1]') == [["a", 1]]
    assert sheets_append.normalize_rows([["a"], ["b"]]) == [["a"], ["b"]]
    assert sheets_append.normalize_rows({"name": "x", "n": 2}) == [["x", 2]]
    assert sheets_append.normalize_rows(["a", "b", 3]) == [["a", "b", 3]]
    assert sheets_append.normalize_rows(42) == [[42]]
    with pytest.raises(NodeExecutionError):
        sheets_append.normalize_rows("not json {")
    with pytest.raises(NodeExecutionError):
        sheets_append.normalize_rows("")


async def test_sheets_append_from_url_id(transport):
    transport.handler = lambda r: httpx.Response(
        200,
        json={"updates": {"updatedRange": "Sheet1!A5:B5", "updatedRows": 1, "updatedCells": 2}},
    )
    result = await sheets_append.run(
        make_ctx(
            {
                "spreadsheet_id": "https://docs.google.com/spreadsheets/d/SHEET_ID_12345/edit#gid=0",
                "sheet_range": "Sheet1",
                "values": '["a", "b"]',
            }
        )
    )
    request = transport.requests[0]
    assert "/SHEET_ID_12345/values/Sheet1:append" in str(request.url)
    assert request.url.params["valueInputOption"] == "USER_ENTERED"
    assert json.loads(request.content) == {"values": [["a", "b"]]}
    assert result["updated_rows"] == 1


async def test_sheets_read_as_objects(transport):
    transport.handler = lambda r: httpx.Response(
        200,
        json={"range": "Sheet1!A1:B3", "values": [["name", "age"], ["ada", "36"], ["alan", "41"]]},
    )
    result = await sheets_read.run(
        make_ctx({"spreadsheet_id": "SHEET_ID_12345", "as_objects": True})
    )
    assert result["rows"] == [{"name": "ada", "age": "36"}, {"name": "alan", "age": "41"}]
    assert result["count"] == 2


# ---------- calendar ----------


async def test_calendar_create_timed_event(transport):
    transport.handler = lambda r: httpx.Response(
        200, json={"id": "ev1", "htmlLink": "https://cal/ev1", "status": "confirmed"}
    )
    await calendar_create_event.run(
        make_ctx(
            {
                "title": "Sync",
                "start": "2026-07-20T15:00:00",
                "end": "2026-07-20T16:00:00",
                "timezone": "Europe/Paris",
                "attendees": "a@x.com, b@x.com",
            }
        )
    )
    request = transport.requests[0]
    assert request.url.path.endswith("/calendars/primary/events")
    payload = json.loads(request.content)
    assert payload["start"] == {"dateTime": "2026-07-20T15:00:00", "timeZone": "Europe/Paris"}
    assert payload["attendees"] == [{"email": "a@x.com"}, {"email": "b@x.com"}]


async def test_calendar_create_all_day_event(transport):
    transport.handler = lambda r: httpx.Response(200, json={"id": "ev2"})
    await calendar_create_event.run(
        make_ctx({"title": "Holiday", "all_day": True, "start": "2026-07-20", "end": "2026-07-21"})
    )
    payload = json.loads(transport.requests[0].content)
    assert payload["start"] == {"date": "2026-07-20"}
    assert payload["end"] == {"date": "2026-07-21"}


async def test_calendar_list_defaults_time_min_to_now(transport):
    transport.handler = lambda r: httpx.Response(
        200,
        json={
            "items": [
                {
                    "id": "e1",
                    "summary": "Standup",
                    "start": {"dateTime": "2026-07-20T09:00:00Z"},
                    "end": {"dateTime": "2026-07-20T09:15:00Z"},
                    "attendees": [{"email": "a@x.com"}],
                }
            ]
        },
    )
    result = await calendar_list_events.run(make_ctx({}))
    params = transport.requests[0].url.params
    assert params["singleEvents"] == "true"
    assert params["orderBy"] == "startTime"
    assert "T" in params["timeMin"]
    assert result["events"][0]["title"] == "Standup"
    assert result["events"][0]["attendees"] == ["a@x.com"]


# ---------- drive / docs ----------


async def test_drive_upload_multipart(transport):
    transport.handler = lambda r: httpx.Response(
        200,
        json={"id": "f1", "name": "r.txt", "mimeType": "text/plain", "webViewLink": "https://d/f1"},
    )
    result = await drive_upload.run(
        make_ctx({"name": "r.txt", "content": "hello drive", "folder_id": "FOLDER9"})
    )
    request = transport.requests[0]
    assert request.url.params["uploadType"] == "multipart"
    body = request.content.decode()
    assert '"name": "r.txt"' in body
    assert '"parents": ["FOLDER9"]' in body
    assert "hello drive" in body
    assert "multipart/related" in request.headers["Content-Type"]
    assert result["web_view_link"] == "https://d/f1"


async def test_docs_create_with_content(transport):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(":batchUpdate"):
            payload = json.loads(request.content)
            assert payload["requests"][0]["insertText"]["text"] == "doc body"
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"documentId": "D1", "title": "Notes"})

    transport.handler = handler
    result = await docs_create.run(make_ctx({"title": "Notes", "content": "doc body"}))
    assert len(transport.requests) == 2
    assert result["document_id"] == "D1"
    assert result["url"] == "https://docs.google.com/document/d/D1/edit"


# ---------- error mapping ----------


async def test_google_401_maps_to_reconnect_hint(transport):
    transport.handler = lambda r: httpx.Response(401, json={"error": {"message": "bad token"}})
    with pytest.raises(NodeExecutionError, match="reconnect the credential"):
        await sheets_read.run(make_ctx({"spreadsheet_id": "SHEET_ID_12345"}))


async def test_google_403_mentions_service_setup(transport):
    transport.handler = lambda r: httpx.Response(
        403, json={"error": {"message": "insufficient scopes"}}
    )
    with pytest.raises(NodeExecutionError, match="insufficient scopes"):
        await gmail_send.run(make_ctx({"to": "a@b.c", "subject": "s", "body": "b"}))
