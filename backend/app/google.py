"""Google OAuth2: consent URL, code exchange, token refresh, account lookup.

A credential stores the user's own OAuth client (client_id/client_secret from
the Google Cloud Console) plus the tokens obtained on consent — the n8n model.
"""

import time
from typing import Any
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# Service -> scopes, kept minimal per service (n8n-style granular consent).
SERVICE_SCOPES: dict[str, list[str]] = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
    ],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "drive": ["https://www.googleapis.com/auth/drive.file"],
    "docs": ["https://www.googleapis.com/auth/documents"],
}


class GoogleOAuthError(Exception):
    pass


def scopes_for(services: list[str]) -> list[str]:
    scopes = ["openid", "email"]
    for service in services:
        scopes.extend(SERVICE_SCOPES.get(service, []))
    return scopes


def build_auth_url(client_id: str, redirect_uri: str, scopes: list[str], state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "access_type": "offline",  # get a refresh token
        "prompt": "consent",  # force refresh token even on re-consent
        "include_granted_scopes": "true",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    client_id: str, client_secret: str, code: str, redirect_uri: str
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
    if response.status_code != 200:
        raise GoogleOAuthError(
            f"Token exchange failed ({response.status_code}): {response.text[:300]}"
        )
    return response.json()


async def refresh_access_token(
    client_id: str, client_secret: str, refresh_token: str
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code != 200:
        raise GoogleOAuthError(
            f"Token refresh failed ({response.status_code}): {response.text[:300]}. "
            "Reconnect the credential."
        )
    return response.json()


async def fetch_account_email(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
    if response.status_code != 200:
        return ""
    return response.json().get("email", "")


def token_expiry(expires_in: Any) -> float:
    try:
        return time.time() + float(expires_in)
    except (TypeError, ValueError):
        return time.time() + 3600
