from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.category import Category
from app.models.tag import Tag, skill_tags
from app.models.user import User


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), index=True)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    install_count: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped[Category] = relationship(back_populates="skills")
    author: Mapped[User] = relationship(back_populates="skills")
    tags: Mapped[list[Tag]] = relationship(secondary=skill_tags, back_populates="skills")
