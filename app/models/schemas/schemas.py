from fastapi import Query
from pydantic import BaseModel


class HTTPError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            'example': {'detail': 'HTTPException raised.'}
        }


class Pager(BaseModel):
    page: int = Query(default=1, ge=1)
    per_page: int = Query(default=10, ge=1)
