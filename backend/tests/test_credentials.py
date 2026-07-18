"""Credentials vault tests: encryption, CRUD, OAuth flow, run-time resolution."""

import time

import pytest
from fastapi.testclient import TestClient

from app import google
from app.db import SessionLocal
from app.engine.credentials import resolve_credential
from app.engine.types import NodeExecutionError
from app.main import app
from app.models import Credential
from app.security import decrypt_json, encrypt_json


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        response = c.post(
            "/api/auth/register",
            json={"username": "creduser", "email": "cred@example.com", "password": "secret123"},
        )
        assert response.status_code == 200
        yield c


def test_encrypt_decrypt_roundtrip():
    data = {"client_secret": "s3cret", "nested": {"a": 1}}
    assert decrypt_json(encrypt_json(data)) == data


def test_create_list_delete_credential(client):
    created = client.post(
        "/api/credentials",
        json={
            "name": "My Google",
            "client_id": "abc123.apps.googleusercontent.com",
            "client_secret": "shhh-secret",
            "services": ["gmail", "sheets"],
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["redirect_uri"].endswith("/api/oauth/google/callback")
    cred = body["credential"]
    assert cred["connected"] is False
    assert cred["services"] == ["gmail", "sheets"]

    listed = client.get("/api/credentials").json()["credentials"]
    assert any(c["id"] == cred["id"] for c in listed)
    # secrets never leave the API
    assert "client_secret" not in str(listed)

    assert client.delete(f"/api/credentials/{cred['id']}").status_code == 200
    listed = client.get("/api/credentials").json()["credentials"]
    assert not any(c["id"] == cred["id"] for c in listed)


def test_unknown_service_rejected(client):
    response = client.post(
        "/api/credentials",
        json={
            "name": "bad",
            "client_id": "abc123.apps.googleusercontent.com",
            "client_secret": "shhh-secret",
            "services": ["gmail", "myspace"],
        },
    )
    assert response.status_code == 422
    assert "myspace" in response.json()["detail"]


def test_oauth_start_builds_consent_url(client):
    created = client.post(
        "/api/credentials",
        json={
            "name": "OAuth flow",
            "client_id": "flowclient.apps.googleusercontent.com",
            "client_secret": "flow-secret",
            "services": ["calendar"],
        },
    ).json()["credential"]

    start = client.get(f"/api/credentials/{created['id']}/oauth/start")
    assert start.status_code == 200
    url = start.json()["url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "flowclient.apps.googleusercontent.com" in url
    assert "calendar" in url
    assert "access_type=offline" in url
    assert "state=" in url


def test_oauth_callback_stores_tokens(client, monkeypatch):
    created = client.post(
        "/api/credentials",
        json={
            "name": "Callback test",
            "client_id": "cb.apps.googleusercontent.com",
            "client_secret": "cb-secret",
            "services": ["gmail"],
        },
    ).json()["credential"]

    start_url = client.get(f"/api/credentials/{created['id']}/oauth/start").json()["url"]
    state = start_url.split("state=")[1].split("&")[0]

    async def fake_exchange(client_id, client_secret, code, redirect_uri):
        assert code == "auth-code-123"
        return {"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 3600}

    async def fake_email(access_token):
        return "tester@gmail.com"

    monkeypatch.setattr(google, "exchange_code", fake_exchange)
    monkeypatch.setattr(google, "fetch_account_email", fake_email)

    response = client.get(f"/api/oauth/google/callback?code=auth-code-123&state={state}")
    assert response.status_code == 200
    assert "connected" in response.text.lower()

    cred = client.get("/api/credentials").json()["credentials"]
    row = next(c for c in cred if c["id"] == created["id"])
    assert row["connected"] is True
    assert row["account_email"] == "tester@gmail.com"


def test_oauth_callback_rejects_bad_state(client):
    response = client.get("/api/oauth/google/callback?code=x&state=forged")
    assert response.status_code == 200
    assert "failed" in response.text.lower()


async def test_resolver_refreshes_expired_token(client, monkeypatch):
    db = SessionLocal()
    me = client.get("/api/auth/me").json()["user"]
    cred = Credential(
        user_id=me["id"],
        name="resolver test",
        type="google_oauth2",
        connected=True,
        data=encrypt_json(
            {
                "client_id": "rc",
                "client_secret": "rs",
                "services": ["gmail"],
                "refresh_token": "rt-old",
                "access_token": "at-expired",
                "expires_at": time.time() - 10,
            }
        ),
    )
    db.add(cred)
    db.commit()
    cred_id = cred.id
    db.close()

    async def fake_refresh(client_id, client_secret, refresh_token):
        assert refresh_token == "rt-old"
        return {"access_token": "at-fresh", "expires_in": 3600}

    monkeypatch.setattr(google, "refresh_access_token", fake_refresh)

    resolved = await resolve_credential(me["id"], cred_id)
    assert resolved["access_token"] == "at-fresh"

    # refreshed token persisted encrypted
    db = SessionLocal()
    stored = decrypt_json(db.get(Credential, cred_id).data)
    db.close()
    assert stored["access_token"] == "at-fresh"
    assert stored["expires_at"] > time.time()


async def test_resolver_rejects_other_users_credential(client):
    me = client.get("/api/auth/me").json()["user"]
    with pytest.raises(NodeExecutionError, match="not found"):
        await resolve_credential(me["id"] + 999, 1)


async def test_resolver_requires_connection(client):
    created = client.post(
        "/api/credentials",
        json={
            "name": "never connected",
            "client_id": "nc.apps.googleusercontent.com",
            "client_secret": "nc-secret",
            "services": ["docs"],
        },
    ).json()["credential"]
    me = client.get("/api/auth/me").json()["user"]
    with pytest.raises(NodeExecutionError, match="not connected"):
        await resolve_credential(me["id"], created["id"])
