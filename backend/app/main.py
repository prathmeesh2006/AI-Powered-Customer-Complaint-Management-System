import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import complaints as complaint_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Create database tables on startup."""
    from app.db.session import engine
    from app.db.base import Base
    import app.models.complaint  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")
    logger.info("Using LLM model: %s", settings.groq_model)
    yield


app = FastAPI(
    title="AIVOA Complaint Management API",
    description="AI-powered pharmaceutical customer complaint intake and QMS workflow",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





# Include routes
app.include_router(complaint_routes.router)


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "model": settings.groq_model,
        "env": settings.app_env,
    }
