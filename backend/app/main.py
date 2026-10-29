"""Punkt wejścia FastAPI."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assignments, auth, availability, dashboard, geocode, licenses, matches, optimization, publications, referees, settings, users, venues
from app.api.deps import require_admin
from app.config import get_config


@asynccontextmanager
async def lifespan(_: FastAPI):
    cfg = get_config()
    if cfg.auto_create_tables:
        from app.database.init_db import init_db

        init_db(seed=cfg.seed_on_startup)
    yield


def create_app() -> FastAPI:
    cfg = get_config()
    app = FastAPI(
        title=cfg.app_name,
        description="Automatyczne układanie obsady sędziowskiej — MVP",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    # Cała reszta API tylko dla zalogowanego obsadzającego.
    admin_only = [Depends(require_admin)]
    for module in (referees, venues, geocode, licenses, matches, availability, assignments, optimization, publications,
                   settings, dashboard, users):
        app.include_router(module.router, dependencies=admin_only)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
