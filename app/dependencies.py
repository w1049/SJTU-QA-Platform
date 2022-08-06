from fastapi import Request, HTTPException

from .database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_user(request: Request):
    user = request.session.get('user_id')
    if user is not None:
        return user
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials.")
