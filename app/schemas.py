from datetime import datetime
from typing import List, Optional

from fastapi import Query
from pydantic import BaseModel

from .models import EnumRole, EnumPermission


class UserModel(BaseModel):
    id: int
    name: str
    institution: str
    role: EnumRole

    class Config:
        orm_mode = True


class QuestionModel(BaseModel):
    id: int
    title: str
    content: str
    # embedding: str
    modified_at: datetime
    modified_by_id: int
    # modified_by: UserModel
    # belongs: List = []
    created_at: datetime
    created_by_id: int

    # created_by: UserModel

    class Config:
        orm_mode = True

    def __hash__(self):
        return self.id


class QuestionSetModel(BaseModel):
    id: int
    name: str
    owner_id: int
    # owner: UserModel
    # maintainer: List[UserModel] = []
    modified_at: datetime
    modified_by_id: int
    # modified_by: UserModel
    created_at: datetime
    created_by_id: int
    # created_by: UserModel
    permission: EnumPermission

    # passwd

    class Config:
        orm_mode = True


class UserA(BaseModel):
    name: str

    class Config:
        orm_mode = True


class QuestionA(BaseModel):
    id: int
    title: str
    modified_at: datetime
    modified_by: UserA
    created_at: datetime
    created_by: UserA

    class Config:
        orm_mode = True


class QuestionListPage(BaseModel):
    page: int = 1
    per_page: int = 10
    total: int = 0
    pages: int = 1
    items: List[QuestionA] = []


class QuestionSetRead(QuestionSetModel):
    question_ids: List[int] = []


class QuestionCreate(BaseModel):
    title: str
    content: str


class QuestionUpdate(BaseModel):
    title: str
    content: str


class QuestionSetCreate(BaseModel):
    name: str


class QuestionSetUpdate(BaseModel):
    operation: str
    name: Optional[str]
    question_ids: Optional[List[int]]


class HTTPError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            'example': {'detail': 'HTTPException raised.'}
        }


class Pager(BaseModel):
    page: int = Query(default=1, ge=1)
    per_page: Optional[int] = Query(default=10, ge=1)
