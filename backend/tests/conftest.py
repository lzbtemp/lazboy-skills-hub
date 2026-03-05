import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.database import Base
from app.main import app
from app.models import Category, User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)

    # Create FTS5 table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                name, description, content,
                content='skills', content_rowid='id'
            )
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS skills_ai AFTER INSERT ON skills BEGIN
                INSERT INTO skills_fts(rowid, name, description, content)
                VALUES (new.id, new.name, new.description, new.content);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS skills_ad AFTER DELETE ON skills BEGIN
                INSERT INTO skills_fts(skills_fts, rowid, name, description, content)
                VALUES ('delete', old.id, old.name, old.description, old.content);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS skills_au AFTER UPDATE ON skills BEGIN
                INSERT INTO skills_fts(skills_fts, rowid, name, description, content)
                VALUES ('delete', old.id, old.name, old.description, old.content);
                INSERT INTO skills_fts(rowid, name, description, content)
                VALUES (new.id, new.name, new.description, new.content);
            END
        """))
        conn.commit()

    # Seed test data
    db = TestSessionLocal()
    if db.query(Category).count() == 0:
        cat = Category(name="Development", slug="development", icon="code", sort_order=0)
        db.add(cat)
        user = User(
            username="testuser",
            email="test@test.com",
            hashed_password=pwd_context.hash("test123"),
            display_name="Test User",
            role="admin",
        )
        db.add(user)
        db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS skills_fts"))
        conn.execute(text("DROP TRIGGER IF EXISTS skills_ai"))
        conn.execute(text("DROP TRIGGER IF EXISTS skills_ad"))
        conn.execute(text("DROP TRIGGER IF EXISTS skills_au"))
        conn.commit()


@pytest.fixture
def client():
    return TestClient(app)
