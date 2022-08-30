from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, validator
from sqlalchemy.orm import Query

from .user import UserName
from ..models import EnumPermission


class QuestionSetDetail(BaseModel):
    """问题库的详细信息"""
    id: int
    name: str
    description: Optional[str]
    question_ids: List[int] = []
    owner: UserName
    maintainer: List[UserName] = []
    modified_at: datetime
    modified_by: UserName
    created_at: datetime
    created_by: UserName
    permission: EnumPermission

    # passwd

    class Config:
        orm_mode = True

    @validator("*", pre=True)
    def evaluate_lazy_columns(cls, v):
        if isinstance(v, Query):
            return v.all()
        return v


class QuestionSetList(BaseModel):
    """用于批量列出问题库"""
    id: int
    name: str
    description: Optional[str]
    owner: UserName
    created_at: datetime
    permission: EnumPermission

    class Config:
        orm_mode = True


class QuestionSetCreate(BaseModel):
    """用于创建问题库"""
    name: str
    description: Optional[str]
    permission: EnumPermission = EnumPermission.private


class QuestionSetCreated(QuestionSetCreate):
    """创建后返回的信息"""
    id: int

    class Config:
        orm_mode = True


class QuestionSetUpdate(BaseModel):
    """用于更新问题库"""
    name: Optional[str]
    description: Optional[str]
    append_qids: Optional[List[int]]
    remove_qids: Optional[List[int]]
    permission: Optional[str]
