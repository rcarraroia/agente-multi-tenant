from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class BaseResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None

class PaginationParams(BaseModel):
    page: int = 1
    limit: int = 10

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    limit: int
    has_more: bool
