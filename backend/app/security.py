"""Encryption for stored credentials: Fernet keyed off the app secret."""

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import SECRET_KEY

_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()))


def encrypt_json(data: dict[str, Any]) -> str:
    return _fernet.encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str) -> dict[str, Any]:
    try:
        return json.loads(_fernet.decrypt(token.encode()))
    except (InvalidToken, json.JSONDecodeError) as e:
        raise ValueError("Stored credential cannot be decrypted (secret key changed?)") from e
