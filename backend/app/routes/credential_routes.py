from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import google
from app.auth import get_current_user
from app.config import PUBLIC_URL, SECRET_KEY
from app.db import get_db
from app.models import Credential, User
from app.security import decrypt_json, encrypt_json

router = APIRouter(tags=["credentials"])

_state_signer = URLSafeTimedSerializer(SECRET_KEY, salt="google-oauth-state")

REDIRECT_URI = f"{PUBLIC_URL}/api/oauth/google/callback"
STATE_MAX_AGE = 600


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    client_id: str = Field(min_length=10, max_length=300)
    client_secret: str = Field(min_length=5, max_length=300)
    services: list[str] = Field(min_length=1)


def _credential_out(cred: Credential, services: list[str]) -> dict:
    return {
        "id": cred.id,
        "name": cred.name,
        "type": cred.type,
        "services": services,
        "account_email": cred.account_email,
        "connected": cred.connected,
        "created_at": cred.created_at.isoformat(),
    }


@router.get("/api/credentials")
def list_credentials(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Credential)
        .filter(Credential.user_id == user.id)
        .order_by(Credential.created_at.desc())
        .all()
    )
    out = []
    for cred in rows:
        try:
            services = decrypt_json(cred.data).get("services", [])
        except ValueError:
            services = []
        out.append(_credential_out(cred, services))
    return {"credentials": out}


@router.post("/api/credentials")
def create_credential(
    body: CredentialCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    unknown = [s for s in body.services if s not in google.SERVICE_SCOPES]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown services: {', '.join(unknown)}. "
            f"Available: {', '.join(google.SERVICE_SCOPES)}",
        )
    cred = Credential(
        user_id=user.id,
        name=body.name,
        type="google_oauth2",
        data=encrypt_json(
            {
                "client_id": body.client_id,
                "client_secret": body.client_secret,
                "services": body.services,
            }
        ),
    )
    db.add(cred)
    db.commit()
    return {"credential": _credential_out(cred, body.services), "redirect_uri": REDIRECT_URI}


@router.delete("/api/credentials/{credential_id}")
def delete_credential(
    credential_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    cred = (
        db.query(Credential)
        .filter(Credential.id == credential_id, Credential.user_id == user.id)
        .first()
    )
    if cred is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(cred)
    db.commit()
    return {"ok": True}


@router.get("/api/credentials/{credential_id}/oauth/start")
def oauth_start(
    credential_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    cred = (
        db.query(Credential)
        .filter(Credential.id == credential_id, Credential.user_id == user.id)
        .first()
    )
    if cred is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    data = decrypt_json(cred.data)
    state = _state_signer.dumps({"cid": cred.id, "uid": user.id})
    url = google.build_auth_url(
        client_id=data["client_id"],
        redirect_uri=REDIRECT_URI,
        scopes=google.scopes_for(data.get("services", [])),
        state=state,
    )
    return {"url": url, "redirect_uri": REDIRECT_URI}


def _callback_page(title: str, message: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html><html><head><title>{title}</title><style>
        body {{ font-family: system-ui, sans-serif; background: #14110d; color: #f4efe6;
               display: flex; align-items: center; justify-content: center;
               height: 100vh; margin: 0; }}
        .card {{ background: #1b1712; border: 1px solid #2e281f; border-radius: 14px;
                padding: 36px 44px; text-align: center; max-width: 420px; }}
        h1 {{ font-size: 20px; margin: 0 0 10px; }}
        p {{ color: #a89c8a; font-size: 14px; line-height: 1.6; margin: 0; }}
        a {{ color: #ffb224; }}
        </style></head><body><div class="card">
        <h1>{title}</h1><p>{message}</p></div></body></html>"""
    )


@router.get("/api/oauth/google/callback")
async def oauth_callback(request: Request, db: Session = Depends(get_db)):
    error = request.query_params.get("error")
    if error:
        return _callback_page(
            "Connection cancelled",
            f"Google returned: {error}. Close this tab and try again from Swarm.",
        )

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        return _callback_page(
            "Connection failed",
            "Missing code or state in the callback. Close this tab and try again.",
        )

    try:
        payload = _state_signer.loads(state, max_age=STATE_MAX_AGE)
    except BadSignature:
        return _callback_page(
            "Connection failed",
            "The sign-in link expired or was tampered with. Close this tab and try again.",
        )

    cred = db.get(Credential, int(payload["cid"]))
    if cred is None or cred.user_id != int(payload["uid"]):
        return _callback_page("Connection failed", "Credential no longer exists. Close this tab.")

    data = decrypt_json(cred.data)
    try:
        tokens = await google.exchange_code(
            data["client_id"], data["client_secret"], code, REDIRECT_URI
        )
    except google.GoogleOAuthError as e:
        return _callback_page("Connection failed", str(e))

    data["access_token"] = tokens.get("access_token", "")
    data["expires_at"] = google.token_expiry(tokens.get("expires_in"))
    if tokens.get("refresh_token"):
        data["refresh_token"] = tokens["refresh_token"]

    account_email = await google.fetch_account_email(data["access_token"])
    cred.data = encrypt_json(data)
    cred.account_email = account_email
    cred.connected = bool(data.get("refresh_token"))
    db.commit()

    if not cred.connected:
        return _callback_page(
            "Almost there",
            "Google did not return a refresh token. Remove this app from your Google account "
            "permissions and connect again.",
        )
    return _callback_page(
        "Google account connected",
        f"{account_email or 'Your account'} is now linked to '{cred.name}'. "
        "Close this tab and return to Swarm.",
    )
