from typing import Optional

from pydantic import BaseModel

from ..models import EnumRole


class UserDetail(BaseModel):
    id: int
    name: str
    institution: Optional[str]
    role: EnumRole

    class Config:
        orm_mode = True


class UserName(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
