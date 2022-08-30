from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from .user import UserName


class QuestionDetail(BaseModel):
    """问题的详细信息"""
    id: int
    title: str
    content: str
    modified_at: datetime
    modified_by: UserName
    created_at: datetime
    created_by: UserName

    class Config:
        orm_mode = True

    def __hash__(self):
        return self.id


class QuestionCreate(BaseModel):
    """用于创建问题"""
    title: str
    content: str
    sid: Optional[int] = None


class QuestionCreated(QuestionCreate):
    """创建后返回的信息"""
    id: int

    class Config:
        orm_mode = True


class QuestionUpdate(BaseModel):
    """用于更新问题"""
    title: Optional[str]
    content: Optional[str]


class QuestionList(BaseModel):
    """用于批量列出问题"""
    id: int
    title: str
    modified_at: datetime
    modified_by: UserName

    class Config:
        orm_mode = True


class QuestionListPage(BaseModel):
    """分页后的列出问题"""
    page: int = 1
    per_page: int = 10
    total: int = 0
    pages: int = 1
    items: List[QuestionList] = []
