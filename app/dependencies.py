from typing import Optional

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from .utils.database import SessionLocal


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_logged_user(request: Request) -> int:
    user_id = request.session.get('user_id')
    if user_id is not None:
        return user_id
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please login")


def get_user(request: Request) -> Optional[int]:
    return request.session.get('user_id')
