from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import admin, analytics, auth, companies, exercises
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime import get_orchestrator
from app.db.base import Base
from app.db.models import RegulatoryReference  # noqa: F401
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    Base.metadata.create_all(bind=engine)
    if settings.environment.casefold() == "production" and settings.secret_key in {
        "change-me-before-deployment",
        "replace-with-a-random-secret-at-least-16-characters",
    }:
        raise RuntimeError("SECRET_KEY deve ser definida em produção.")
    get_orchestrator()
    yield
    get_orchestrator().close()


app = FastAPI(
    title="CyberSim AI",
    description="Plataforma fictícia de treinamento para simulação de crises cibernéticas.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(exercises.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Saúde"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version, "llm_provider": settings.llm_provider}
