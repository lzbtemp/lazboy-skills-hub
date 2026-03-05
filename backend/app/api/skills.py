import math

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from slugify import slugify
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models import Category, Skill, Tag
from app.schemas.skill import (
    PaginatedResponse,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.get("", response_model=PaginatedResponse)
def list_skills(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = None,
    tag: str | None = None,
    sort: str = Query("newest", pattern="^(newest|popular|name)$"),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Skill)
        .options(joinedload(Skill.category), joinedload(Skill.author), joinedload(Skill.tags))
        .filter(Skill.is_published.is_(True))
    )

    if category:
        query = query.join(Category).filter(Category.slug == category)

    if tag:
        query = query.join(Skill.tags).filter(Tag.slug == tag)

    if sort == "newest":
        query = query.order_by(Skill.created_at.desc())
    elif sort == "popular":
        query = query.order_by(Skill.install_count.desc())
    elif sort == "name":
        query = query.order_by(Skill.name.asc())

    total = query.count()
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    skills = query.offset((page - 1) * per_page).limit(per_page).all()

    return PaginatedResponse(
        data=skills,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{slug}", response_model=SkillResponse)
def get_skill(slug: str, db: Session = Depends(get_db)):
    skill = (
        db.query(Skill)
        .options(joinedload(Skill.category), joinedload(Skill.author), joinedload(Skill.tags))
        .filter(Skill.slug == slug)
        .first()
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("", response_model=SkillResponse, status_code=201)
def create_skill(data: SkillCreate, db: Session = Depends(get_db)):
    # Verify category exists
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Invalid category_id")

    slug = slugify(data.name)
    if db.query(Skill).filter(Skill.slug == slug).first():
        raise HTTPException(status_code=409, detail="A skill with this name already exists")

    # Resolve or create tags
    tags = _resolve_tags(db, data.tag_names)

    # Use author_id=1 (admin) as placeholder until auth is implemented
    skill = Skill(
        name=data.name,
        slug=slug,
        description=data.description,
        content=data.content,
        version=data.version,
        category_id=data.category_id,
        author_id=1,
        tags=tags,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    return (
        db.query(Skill)
        .options(joinedload(Skill.category), joinedload(Skill.author), joinedload(Skill.tags))
        .filter(Skill.id == skill.id)
        .first()
    )


@router.put("/{slug}", response_model=SkillResponse)
def update_skill(slug: str, data: SkillUpdate, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.slug == slug).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if data.name is not None:
        skill.name = data.name
        skill.slug = slugify(data.name)
    if data.description is not None:
        skill.description = data.description
    if data.content is not None:
        skill.content = data.content
    if data.version is not None:
        skill.version = data.version
    if data.category_id is not None:
        category = db.query(Category).filter(Category.id == data.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category_id")
        skill.category_id = data.category_id
    if data.tag_names is not None:
        skill.tags = _resolve_tags(db, data.tag_names)

    db.commit()
    db.refresh(skill)

    return (
        db.query(Skill)
        .options(joinedload(Skill.category), joinedload(Skill.author), joinedload(Skill.tags))
        .filter(Skill.id == skill.id)
        .first()
    )


@router.delete("/{slug}", status_code=204)
def delete_skill(slug: str, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.slug == slug).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(skill)
    db.commit()


@router.get("/{slug}/download")
def download_skill(slug: str, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.slug == slug).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return PlainTextResponse(
        content=skill.content,
        headers={"Content-Disposition": f'attachment; filename="SKILL.md"'},
    )


@router.post("/{slug}/install", status_code=200)
def record_install(slug: str, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.slug == slug).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.install_count += 1
    db.commit()
    return {"install_count": skill.install_count}


def _resolve_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    tags = []
    for name in tag_names:
        tag_slug = slugify(name)
        tag = db.query(Tag).filter(Tag.slug == tag_slug).first()
        if not tag:
            tag = Tag(name=name.lower(), slug=tag_slug)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags
