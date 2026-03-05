from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Category, Skill
from app.schemas.category import CategoryResponse, CategoryWithCount

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.sort_order).all()


@router.get("/{slug}", response_model=CategoryWithCount)
def get_category(slug: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    skill_count = (
        db.query(func.count(Skill.id))
        .filter(Skill.category_id == category.id, Skill.is_published.is_(True))
        .scalar()
    )

    result = CategoryWithCount.model_validate(category)
    result.skill_count = skill_count
    return result
