from datetime import datetime

from pydantic import BaseModel

from app.schemas.category import CategoryResponse
from app.schemas.user import UserResponse


class TagResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


class SkillCreate(BaseModel):
    name: str
    description: str
    content: str
    version: str = "1.0.0"
    category_id: int
    tag_names: list[str] = []


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None
    version: str | None = None
    category_id: int | None = None
    tag_names: list[str] | None = None


class SkillResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    content: str
    version: str
    install_count: int
    is_published: bool
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse
    author: UserResponse
    tags: list[TagResponse]

    model_config = {"from_attributes": True}


class SkillListItem(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    version: str
    install_count: int
    created_at: datetime
    category: CategoryResponse
    author: UserResponse
    tags: list[TagResponse]

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    data: list[SkillListItem]
    page: int
    per_page: int
    total: int
    total_pages: int
