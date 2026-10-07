"""
app/main.py - FastAPI application factory.

Creates the app instance, configures middleware (CORS, Request ID), attaches
routers, handles global errors, and ensures the database schema is created on startup.
"""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import jobs, verify

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Creates all database tables on startup.
    FastAPI calls this with an async context manager on startup and shutdown.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized with all tables and indexes.")
    yield
    # Clean shutdown hook
    engine.dispose()
    logger.info("Database engine connections closed.")


def create_app() -> FastAPI:
    """
    Application factory that creates and configures the FastAPI instance.

    Using a factory function (rather than a module-level app object) makes
    it easy to create isolated app instances in tests without side-effects.
    """
    app = FastAPI(
        title="Bulk Certificate Generator API",
        description=(
            "Production-ready backend API for asynchronous bulk PDF certificate generation. "
            "Accepts recipient cohorts, processes PDF generation via ReportLab, "
            "tracks real-time progress counters, and provides secure download endpoints."
        ),
        version="1.0.0",
        lifespan=lifespan,
        contact={
            "name": "Aereo SDE Intern Assignment",
        },
        license_info={
            "name": "MIT",
        },
    )

    # ---------------------------------------------------------------------------
    # Request Tracing Middleware
    # ---------------------------------------------------------------------------
    @app.middleware("http")
    async def request_tracing_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ---------------------------------------------------------------------------
    # Global Exception Handler
    # ---------------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected internal server error occurred."},
        )

    # ---------------------------------------------------------------------------
    # CORS Middleware
    # ---------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------------------
    # Routers
    # ---------------------------------------------------------------------------
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(verify.router, prefix="/api/v1")
    app.include_router(verify.router, prefix="")

    # ---------------------------------------------------------------------------
    # Health-check endpoints
    # ---------------------------------------------------------------------------
    @app.get("/health", tags=["Health"], summary="Service health check")
    @app.get("/api/v1/health", tags=["Health"], summary="Service health check (versioned)")
    def health_check() -> dict:
        """Returns service status confirmation."""
        return {
            "status": "ok",
            "service": "bulk-certificate-generator",
            "environment": settings.ENVIRONMENT,
        }

    # ---------------------------------------------------------------------------
    # Frontend SPA Mount (if built)
    # ---------------------------------------------------------------------------
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


# Create the app instance used by uvicorn
app = create_app()
