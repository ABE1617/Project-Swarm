"""Resolve a node's credential reference to fresh secrets at run time."""

import time
from typing import Any

from app import google
from app.db import SessionLocal
from app.engine.types import NodeExecutionError
from app.models import Credential
from app.security import decrypt_json, encrypt_json

REFRESH_MARGIN_SECONDS = 60


async def resolve_credential(user_id: int, credential_id: Any) -> dict:
    try:
        cid = int(credential_id)
    except (TypeError, ValueError):
        raise NodeExecutionError("Select a credential in the node settings") from None

    db = SessionLocal()
    try:
        cred = db.get(Credential, cid)
        if cred is None or cred.user_id != user_id:
            raise NodeExecutionError("Credential not found - select one in the node settings")
        data = decrypt_json(cred.data)

        if cred.type == "google_oauth2":
            if not data.get("refresh_token"):
                raise NodeExecutionError(
                    f"Credential '{cred.name}' is not connected to Google yet - "
                    "open Credentials and finish the connection"
                )
            if float(data.get("expires_at", 0)) < time.time() + REFRESH_MARGIN_SECONDS:
                try:
                    refreshed = await google.refresh_access_token(
                        data["client_id"], data["client_secret"], data["refresh_token"]
                    )
                except google.GoogleOAuthError as e:
                    raise NodeExecutionError(str(e)) from None
                data["access_token"] = refreshed["access_token"]
                data["expires_at"] = google.token_expiry(refreshed.get("expires_in"))
                if refreshed.get("refresh_token"):
                    data["refresh_token"] = refreshed["refresh_token"]
                cred.data = encrypt_json(data)
                db.commit()
            return {
                "type": cred.type,
                "name": cred.name,
                "account_email": cred.account_email,
                "access_token": data["access_token"],
            }

        return {"type": cred.type, "name": cred.name, **data}
    finally:
        db.close()
