"""
AI-Powered Task Summarizer API
Main application entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Cleanup resources if needed


def create_application() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        description="A REST API service that manages tasks with AI-powered summarization capabilities",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup custom exception handlers
    setup_exception_handlers(application)

    # Include API routes
    application.include_router(api_router, prefix="/api/v1")

    return application


app = create_application()


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify service status."""
    return {"status": "healthy", "service": settings.APP_NAME}
