from datetime import datetime

from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    icon: str | None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryWithCount(CategoryResponse):
    skill_count: int = 0
