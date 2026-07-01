from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth.models import User
from app.auth.router import router as auth_router
from app.auth.schemas import UserResponse
from app.agents.router import router as agents_router
from app.conversations.router import router as conversations_router
from app.models.router import router as models_router
from app.shared.auth import get_current_user
from app.shared.config import Settings, get_settings
from app.shared.database import get_db, get_engine, get_session_factory
from app.shared.errors import AppError, app_error_handler, http_exception_handler
from app.shared.logging import setup_logging
from app.skills.router import router as skills_router
from app.quota.router import router as quota_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    try:
        settings = get_settings()
        engine = get_engine(settings)
        factory = get_session_factory(engine)
        db = factory()
        try:
            from app.models.service import seed_model_configs
            from app.shared.seed import seed_local_users
            from app.skills.service import seed_builtin_skills

            seed_local_users(db)
            seed_builtin_skills(db)
            seed_model_configs(db)
        finally:
            db.close()
    except Exception:
        import logging

        logging.getLogger(__name__).warning("Could not seed local users (expected if no database is available)", exc_info=True)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="HR Agent MVP",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, http_exception_handler)

    app.include_router(auth_router)
    app.include_router(skills_router)
    app.include_router(models_router)
    app.include_router(conversations_router)
    app.include_router(agents_router)
    app.include_router(quota_router)

    @app.get("/api/me", response_model=UserResponse)
    def get_me(current_user: User = Depends(get_current_user)):
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            role=current_user.role,
            display_name=current_user.display_name,
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        return {"status": "ready", "database": "not checked"}

    return app


app = create_app()
