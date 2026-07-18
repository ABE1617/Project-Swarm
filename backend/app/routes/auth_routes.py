from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import (
    clear_session_cookie,
    get_current_user,
    hash_password,
    set_session_cookie,
    verify_password,
)
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing = (
        db.query(User).filter(or_(User.username == body.username, User.email == body.email)).first()
    )
    if existing:
        field = "Username" if existing.username == body.username else "Email"
        raise HTTPException(status_code=409, detail=f"{field} is already taken")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    set_session_cookie(response, user.id)
    return {"user": UserOut.model_validate(user, from_attributes=True).model_dump()}


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    set_session_cookie(response, user.id)
    return {"user": UserOut.model_validate(user, from_attributes=True).model_dump()}


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": UserOut.model_validate(user, from_attributes=True).model_dump()}
