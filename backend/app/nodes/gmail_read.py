import base64

from app.engine.types import NodeContext
from app.nodes._google import CREDENTIAL_FIELD, google_api

NODE_TYPE = "gmail_read"
NODE_NAME = "Gmail: Read"
NODE_DESCRIPTION = "Search your inbox and read messages"
NODE_CATEGORY = "Google"
NODE_COLOR = "#EA4335"
NODE_ICON = "gmail"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
NODE_TIMEOUT = 120

GMAIL = "https://gmail.googleapis.com/gmail/v1"

CONFIG_FIELDS = [
    CREDENTIAL_FIELD,
    {"key": "query", "label": "Search query", "type": "string",
     "placeholder": "is:unread from:boss@example.com",
     "help": "Gmail search syntax, same as the Gmail search box. Empty = latest messages."},
    {"key": "max_results", "label": "Max messages", "type": "number", "default": 10,
     "min": 1, "max": 50},
    {"key": "include_body", "label": "Include message body", "type": "boolean", "default": True},
]


def _decode_part(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _extract_body(payload: dict) -> str:
    """Prefer text/plain; fall back to text/html; search nested parts."""
    stack = [payload]
    html_fallback = ""
    while stack:
        part = stack.pop(0)
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime == "text/plain":
            return _decode_part(data)
        if data and mime == "text/html" and not html_fallback:
            html_fallback = _decode_part(data)
        stack.extend(part.get("parts", []))
    return html_fallback


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


async def run(ctx: NodeContext):
    max_results = min(max(int(ctx.config.get("max_results") or 10), 1), 50)
    params: dict = {"maxResults": max_results}
    query = str(ctx.config.get("query") or "").strip()
    if query:
        params["q"] = query

    listing = await google_api(ctx, "GET", f"{GMAIL}/users/me/messages", params=params)
    ids = [m["id"] for m in listing.get("messages", [])]
    ctx.log("info", f"Found {len(ids)} message(s)")

    include_body = ctx.config.get("include_body", True)
    messages = []
    for message_id in ids:
        detail = await google_api(
            ctx,
            "GET",
            f"{GMAIL}/users/me/messages/{message_id}",
            params={"format": "full" if include_body else "metadata"},
        )
        payload = detail.get("payload", {})
        headers = payload.get("headers", [])
        message = {
            "id": detail.get("id"),
            "thread_id": detail.get("threadId"),
            "from": _header(headers, "From"),
            "to": _header(headers, "To"),
            "subject": _header(headers, "Subject"),
            "date": _header(headers, "Date"),
            "snippet": detail.get("snippet", ""),
            "labels": detail.get("labelIds", []),
        }
        if include_body:
            message["body"] = _extract_body(payload)
        messages.append(message)

    return {"count": len(messages), "messages": messages}
