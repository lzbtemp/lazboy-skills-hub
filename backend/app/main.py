from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.categories import router as categories_router
from app.api.skills import router as skills_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="La-Z-Boy Skills Repository",
        description="Internal skills registry for AI agent capabilities",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(skills_router)
    app.include_router(categories_router)

    @app.get("/api/v1/health")
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
