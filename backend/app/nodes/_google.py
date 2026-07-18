"""Shared Google API plumbing for the Google nodes (underscore = not a node)."""

import re
from typing import Any

import httpx

from app.engine.types import NodeContext, NodeExecutionError

CREDENTIAL_FIELD = {
    "key": "credential",
    "label": "Google account",
    "type": "credential",
    "credential_type": "google_oauth2",
    "required": True,
    "help": "Create and connect one under Credentials",
}

# Tests inject an httpx.MockTransport here to fake Google's API.
TRANSPORT: httpx.AsyncBaseTransport | None = None


def _error_message(response: httpx.Response) -> str:
    try:
        return response.json()["error"]["message"]
    except Exception:
        return response.text[:200]


async def google_api(
    ctx: NodeContext,
    method: str,
    url: str,
    *,
    params: dict | None = None,
    json_body: Any = None,
    content: bytes | None = None,
    headers: dict | None = None,
) -> dict:
    cred = await ctx.get_credential(ctx.config.get("credential"))
    request_headers = {"Authorization": f"Bearer {cred['access_token']}"}
    if headers:
        request_headers.update(headers)

    async with httpx.AsyncClient(timeout=60, transport=TRANSPORT) as client:
        try:
            response = await client.request(
                method, url, params=params, json=json_body, content=content, headers=request_headers
            )
        except httpx.HTTPError as e:
            raise NodeExecutionError(f"Google API request failed: {e}") from None

    if response.status_code == 401:
        raise NodeExecutionError(
            "Google rejected the access token - reconnect the credential under Credentials"
        )
    if response.status_code == 403:
        raise NodeExecutionError(
            f"Google denied access (403): {_error_message(response)}. Make sure the credential "
            "includes this service and the API is enabled in your Google Cloud project."
        )
    if response.status_code == 404:
        raise NodeExecutionError(f"Google resource not found (404): {_error_message(response)}")
    if response.status_code >= 400:
        raise NodeExecutionError(
            f"Google API error {response.status_code}: {_error_message(response)}"
        )
    if not response.content:
        return {}
    return response.json()


def extract_spreadsheet_id(value: str) -> str:
    """Accept a bare spreadsheet id or a full docs.google.com URL."""
    value = str(value).strip()
    match = re.search(r"/d/([a-zA-Z0-9_-]{10,})", value)
    if match:
        return match.group(1)
    if "/" in value or " " in value:
        raise NodeExecutionError(
            "Spreadsheet ID looks invalid - paste the ID or the full spreadsheet URL"
        )
    return value
