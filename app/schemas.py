from datetime import datetime
from typing import List, Optional

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
